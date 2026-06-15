#!/usr/bin/env python3
"""
edu_consulting Tier 3 병렬 정제 러너 (속도·리소스 극대화).

기본 run_edu_tier3.py는 순차(건당 ~40초). 정제는 Gemini API 대기(I/O)가 병목이라
스레드 풀 동시성으로 처리량을 수배 끌어올린다. 두 머신(MBP+Mac Mini)에 작업을
겹치지 않게 나누려면 --shard 로 fs.id 모듈러 분할한다.

  MBP 예:     python scripts/run_edu_tier3_parallel.py --workers 6 --shard 0/2
  Mac Mini 예: python scripts/run_edu_tier3_parallel.py --workers 4 --shard 1/2

- 후보 id를 시작 시점에 스냅샷 → 샤드별로 분리되므로 머신 간 중복 정제 없음.
- 워커마다 자체 DB 연결(execute_query가 호출마다 connect/close → 스레드 안전).
- 비용 가드: 주기적으로 get_today_cost 확인, 한도 초과 시 신규 제출 중단.
- 종료 후 evidence_bank.json 자동 갱신.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(PROJECT_ROOT / ".env", override=True)

from core.database import execute_query  # noqa: E402
from core.logger import HarnessLogger  # noqa: E402
from adapters.content.refiner import (  # noqa: E402
    refine_signal,
    save_refined_output,
    _fallback_refined_output,
    get_today_cost,
    DEFAULT_GEMINI_MODEL,
    DAILY_COST_LIMIT,
)

_stop = threading.Event()
_lock = threading.Lock()
_counters = {"refined": 0, "skipped": 0, "failed": 0}


def _parse_shard(s: str) -> tuple[int, int]:
    try:
        i, n = s.split("/")
        i, n = int(i), int(n)
        if not (0 <= i < n and n >= 1):
            raise ValueError
        return i, n
    except Exception:
        raise SystemExit(f"--shard 형식 오류: '{s}' (예: 0/2)")


def _fetch_candidates(min_score: float, shard_i: int, shard_n: int, limit: int | None) -> list[dict]:
    rows = execute_query(
        """
        SELECT fs.id, fs.title, fs.summary, fs.content_hash, fs.source, fs.score,
               fs.extracted_facts, 'edu_consulting' AS domain
        FROM filtered_signals fs
        LEFT JOIN refined_outputs ro ON fs.id = ro.filtered_signal_id
        LEFT JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        WHERE ro.id IS NULL
          AND fs.domain = 'edu_consulting'
          AND fs.score >= %s
          AND (MOD(fs.id, %s) = %s)
        -- 정렬 정책: (1) freshness floor — 최근 7일 수집분을 먼저 정제한다. 이 러너 출력은
        --   refresh_edu_evidence_bank 가 created_at DESC 로 "fresh evidence"를 구성하므로,
        --   순수 score 우선이면 고점수 오래된 백로그가 최근 신호를 굶겨 최신 근거층이 낡아진다.
        -- (2) 각 신선도 티어 안에서 가치(score) 우선 — 같은 정제 예산을 고가치부터 소진(가성비).
        -- (3) 동점이면 최신 날짜(postdate→수집일), (4) id. → 신선도 보장 + 고가치 우선 양립.
        ORDER BY (CASE WHEN rs.ingested_at >= now() - interval '7 days' THEN 0 ELSE 1 END),
                 fs.score DESC NULLS LAST,
                 COALESCE(NULLIF(rs.raw_data->>'postdate', ''),
                          to_char(rs.ingested_at, 'YYYYMMDD')) DESC,
                 fs.id DESC
        """,
        (min_score, shard_n, shard_i),
        fetch=True,
    ) or []
    return rows[:limit] if limit else rows


def _process_one(model: str, row: dict, logger: HarnessLogger) -> None:
    if _stop.is_set():
        return
    try:
        result = refine_signal(model, dict(row))
    except Exception as e:
        fb = _fallback_refined_output(dict(row), e)
        if fb:
            save_refined_output(row["id"], fb, f"{model}:fallback")
            with _lock:
                _counters["refined"] += 1
            logger.warning(f"  fallback 저장 (id={row['id']}, {type(e).__name__})")
        else:
            with _lock:
                _counters["failed"] += 1
            logger.error(f"  실패 (id={row['id']}): {type(e).__name__}: {e}")
        return

    if not result.get("is_relevant", True):
        with _lock:
            _counters["skipped"] += 1
        return

    rid = save_refined_output(row["id"], result, model)
    with _lock:
        _counters["refined"] += 1
        n = _counters["refined"]
    logger.info(f"  [{n}] 완료(id={rid}): {result['final_title'][:46]}")


def run(workers: int, min_score: float, shard: str, limit: int | None, cost_every: int) -> int:
    shard_i, shard_n = _parse_shard(shard)
    cid = str(uuid.uuid4())[:8]
    logger = HarnessLogger(tier=3, correlation_id=cid)
    logger.info(f"=== edu Tier3 병렬 정제 (run_id={cid}, workers={workers}, shard={shard}) ===")

    rows = _fetch_candidates(min_score, shard_i, shard_n, limit)
    if not rows:
        logger.info("정제 대상 없음")
        return 0
    logger.info(f"정제 대상: {len(rows)}개 (shard {shard}, min_score={min_score})")

    model = DEFAULT_GEMINI_MODEL
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_process_one, model, r, logger): r["id"] for r in rows}
        for fut in as_completed(futures):
            done += 1
            try:
                fut.result()
            except Exception as e:
                logger.error(f"  워커 예외: {e}")
            # 주기적 비용 점검
            if done % cost_every == 0 and not _stop.is_set():
                if get_today_cost(logger) >= DAILY_COST_LIMIT:
                    logger.warning("일일 비용 한도 도달 — 신규 처리 중단")
                    _stop.set()

    logger.info(
        f"=== 완료: 정제 {_counters['refined']} / 스킵 {_counters['skipped']} / 실패 {_counters['failed']} ==="
    )

    # 근거 뱅크 갱신
    try:
        from scripts.refresh_edu_evidence_bank import build_bank, BANK_PATH
        bank = build_bank(window_days=45, max_fresh=25)
        if bank["_meta"]["counts"]["total"] > 0:
            BANK_PATH.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
            c = bank["_meta"]["counts"]
            logger.info(f"[근거 뱅크] 갱신: 총 {c['total']} (앵커 {c['evergreen_anchors']} + 최신 {c['fresh_pipeline']})")
    except Exception as e:
        logger.warning(f"[근거 뱅크] 갱신 실패: {e}")

    # RAG 인덱스 증분 갱신 — 방금 정제된 edu 항목을 같은 실행에서 임베딩해 검색 코퍼스에 반영
    try:
        from scripts.build_edu_evidence_index import build as build_index, INDEX_PATH
        index = build_index(rebuild=False)
        INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        logger.info(f"[RAG 인덱스] 증분 갱신: 총 {index['count']}건")
    except Exception as e:
        logger.warning(f"[RAG 인덱스] 갱신 실패: {e}")

    return _counters["refined"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="edu_consulting Tier 3 병렬 정제")
    ap.add_argument("--workers", type=int, default=6, help="동시 워커 수 (기본 6)")
    ap.add_argument("--min-score", type=float, default=0.1, help="최소 점수 (기본 0.1)")
    ap.add_argument("--shard", type=str, default="0/1", help="샤드 i/n (예: 0/2). 기본 0/1=전체")
    ap.add_argument("--limit", type=int, default=None, help="이번 실행 최대 건수 (기본 전체)")
    ap.add_argument("--cost-every", type=int, default=20, help="N건마다 비용 점검 (기본 20)")
    args = ap.parse_args()
    run(args.workers, args.min_score, args.shard, args.limit, args.cost_every)
