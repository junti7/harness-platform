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
import os
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
# launchd/production environment must remain authoritative; .env only fills gaps.
load_dotenv(PROJECT_ROOT / ".env", override=False)

from core.database import execute_query  # noqa: E402
from core.logger import HarnessLogger  # noqa: E402
from adapters.content.refiner import (  # noqa: E402
    refine_signal,
    save_refined_output,
    _fallback_refined_output,
    _error_skipped_output,
    get_today_cost,
    DEFAULT_GEMINI_MODEL,
    DAILY_COST_LIMIT,
)

_stop = threading.Event()
_lock = threading.Lock()
_counters = {"refined": 0, "skipped": 0, "failed": 0}

EDU_TIER3_SOURCE_ALLOWLIST = [
    "EdWeek",
    "Google_Education_Blog",
    "Brunch_AI교육_학부모",
    "Brunch_자녀교육_AI",
    "Brunch_AI리터러시",
    "youtube_topic_search",
    "youtube_Edutopia",
    "youtube_Common_Sense_Media",
    "EdSurge",
    "Wired_Education",
]

EDU_TIER3_TEXT_GATE_PATTERNS = [
    "%AI%",
    "%인공지능%",
    "%챗GPT%",
    "%ChatGPT%",
    "%생성형%",
    "%디지털교과서%",
    "%디지털 교과서%",
    "%에듀테크%",
    "%코딩%",
    "%프롬프트%",
    "%LLM%",
    "%Gemini%",
    "%Claude%",
    "%Copilot%",
    "%스마트폰%",
    "%digital literacy%",
    "%AI literacy%",
    "%artificial intelligence%",
    "%generative AI%",
]

EDU_TIER3_TEXT_DENY_PATTERNS = [
    "%협약%",
    "%맞손%",
    "%인재 양성%",
    "%인재양성%",
    "%교직원%",
    "%직장인 대상%",
    "%공기업 취업%",
    "%직무 자격증%",
    "%계약학과%",
    "%교사 채용%",
    "%대학생%",
    "%취준생%",
    "%취업 준비%",
    "%취업준비%",
    "%직업 훈련%",
    "%스포츠%",
    "%전력설비%",
    "%교수법 워크숍%",
]

EDU_TIER3_TRIAGE_SKIP_SOURCES = [
    "GoogleNews_취준생AI",
]

EDU_TIER3_TRIAGE_SKIP_PATTERNS = [
    *EDU_TIER3_TEXT_DENY_PATTERNS,
    "%취준생%",
    "%채용%",
    "%공기업%",
    "%직장인%",
    "%대학생%",
    "%대학교%",
    "%한우%",
    "%농가%",
    "%기상캐스터%",
    "%연예%",
    "%전력설비%",
    "%스마트 디톡스%",
    "%로봇 자동화%",
]

EDU_TIER3_AUDIENCE_PATTERNS = [
    "%학부모%",
    "%자녀%",
    "%초등%",
    "%중학%",
    "%중학교%",
    "%고등%",
    "%고교%",
    "%고등학교%",
    "%학교%",
    "%학생%",
    "%교육과정%",
    "%진로%",
    "%교실%",
    "%K-12%",
    "%parents%",
    "%students%",
    "%schools%",
    "%classroom%",
]


def _combined_text_sql() -> str:
    return "(fs.title || chr(32) || COALESCE(fs.summary, ''))"


def _rule_skipped_output(row: dict, reason: str) -> dict:
    title = (row.get("title") or "규칙 기반 폐기 후보").strip()[:120] or "규칙 기반 폐기 후보"
    return {
        "final_title": title,
        "is_relevant": False,
        "evidence_posture": {
            "classification": "speculative",
            "why": f"Rule triage classified this candidate as outside the edu Tier3 refinement scope: {reason}",
        },
        "summary": (row.get("summary") or "").strip()[:600],
        "source": row.get("source") or "",
        "tags": ["tier3-triage-skip", "irrelevant"],
        "triage_reason": reason,
    }


def _triage_reason_sql(text_expr: str) -> str:
    return f"""
               CASE
                 WHEN fs.source = ANY(%s) THEN 'source-skip'
                 WHEN NOT (fs.source = ANY(%s)) THEN 'outside-curated-source-allowlist'
                 WHEN {text_expr} ILIKE ANY(%s) THEN 'text-skip'
                 ELSE 'missing-required-topic-or-audience-signal'
               END AS triage_reason
    """


def _parse_shard(s: str) -> tuple[int, int]:
    try:
        i, n = s.split("/")
        i, n = int(i), int(n)
        if not (0 <= i < n and n >= 1):
            raise ValueError
        return i, n
    except Exception:
        raise SystemExit(f"--shard 형식 오류: '{s}' (예: 0/2)")


def _fetch_candidates(min_score: float, shard_i: int, shard_n: int, limit: int | None, text_gate: bool = True) -> list[dict]:
    text_expr = _combined_text_sql()
    gate_sql = """
          AND fs.source = ANY(%s)
          AND {text_expr} ILIKE ANY(%s)
          AND {text_expr} ILIKE ANY(%s)
          AND NOT ({text_expr} ILIKE ANY(%s))
    """.format(text_expr=text_expr) if text_gate else ""
    params: tuple = (
        min_score,
        shard_n,
        shard_i,
        EDU_TIER3_SOURCE_ALLOWLIST,
        EDU_TIER3_TEXT_GATE_PATTERNS,
        EDU_TIER3_AUDIENCE_PATTERNS,
        EDU_TIER3_TEXT_DENY_PATTERNS,
    ) if text_gate else (min_score, shard_n, shard_i)
    rows = execute_query(
        f"""
        SELECT fs.id, fs.title, fs.summary, fs.content_hash, fs.source, fs.score,
               fs.extracted_facts, 'edu_consulting' AS domain
        FROM filtered_signals fs
        LEFT JOIN refined_outputs ro ON fs.id = ro.filtered_signal_id
        LEFT JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        WHERE ro.id IS NULL
          AND fs.domain = 'edu_consulting'
          AND fs.score >= %s
          AND (MOD(fs.id, %s) = %s)
          {gate_sql}
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
        params,
        fetch=True,
    ) or []
    return rows[:limit] if limit else rows


def _fetch_rule_skip_candidates(min_score: float, shard_i: int, shard_n: int, limit: int) -> list[dict]:
    text_expr = _combined_text_sql()
    rows = execute_query(
        f"""
        SELECT fs.id, fs.title, fs.summary, fs.content_hash, fs.source, fs.score,
               fs.extracted_facts, 'edu_consulting' AS domain,
               {_triage_reason_sql(text_expr)}
        FROM filtered_signals fs
        LEFT JOIN refined_outputs ro ON fs.id = ro.filtered_signal_id
        LEFT JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        WHERE ro.id IS NULL
          AND fs.domain = 'edu_consulting'
          AND fs.score >= %s
          AND (MOD(fs.id, %s) = %s)
          -- Keep gate의 정확한 여집합을 terminal triage 대상으로 삼는다.
          -- 이전 조건은 allowlist 안에 있으나 topic/audience marker가 없는 row를 어느 쪽에도
          -- 넣지 않아 영구 backlog를 만들었다.
          AND NOT (
            fs.source = ANY(%s)
            AND {text_expr} ILIKE ANY(%s)
            AND {text_expr} ILIKE ANY(%s)
            AND NOT ({text_expr} ILIKE ANY(%s))
          )
        ORDER BY (CASE WHEN rs.ingested_at >= now() - interval '7 days' THEN 0 ELSE 1 END),
                 fs.score DESC NULLS LAST,
                 COALESCE(NULLIF(rs.raw_data->>'postdate', ''),
                          to_char(rs.ingested_at, 'YYYYMMDD')) DESC,
                 fs.id DESC
        LIMIT %s
        """,
        (
            EDU_TIER3_TRIAGE_SKIP_SOURCES,
            EDU_TIER3_SOURCE_ALLOWLIST,
            EDU_TIER3_TRIAGE_SKIP_PATTERNS,
            min_score,
            shard_n,
            shard_i,
            EDU_TIER3_SOURCE_ALLOWLIST,
            EDU_TIER3_TEXT_GATE_PATTERNS,
            EDU_TIER3_AUDIENCE_PATTERNS,
            EDU_TIER3_TEXT_DENY_PATTERNS,
            limit,
        ),
        fetch=True,
    ) or []
    return rows


def _triage_rule_skips(min_score: float, shard_i: int, shard_n: int, limit: int, logger: HarnessLogger) -> int:
    if limit <= 0:
        return 0
    rows = _fetch_rule_skip_candidates(min_score, shard_i, shard_n, limit)
    if not rows:
        logger.info("rule triage 폐기 대상 없음")
        return 0

    logger.info(f"rule triage 폐기 대상: {len(rows)}개")
    saved = 0
    for row in rows:
        reason = str(row.get("triage_reason") or "rule-skip")
        save_refined_output(row["id"], _rule_skipped_output(dict(row), reason), "edu-triage:rule-skip")
        saved += 1
        with _lock:
            _counters["skipped"] += 1
            n = _counters["skipped"]
        logger.info(f"  [triage skip {n}] 저장(id={row['id']}): {str(row.get('title') or '')[:46]}")
    return saved


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
            skipped = _error_skipped_output(dict(row), e)
            save_refined_output(row["id"], skipped, f"{model}:error-skip")
            with _lock:
                _counters["skipped"] += 1
                n = _counters["skipped"]
            logger.warning(f"  [skip {n}] 오류 탈락 저장(id={row['id']}): {type(e).__name__}: {e}")
        return

    if not result.get("is_relevant", True):
        save_refined_output(row["id"], result, f"{model}:irrelevant")
        with _lock:
            _counters["skipped"] += 1
            n = _counters["skipped"]
        title = str(result.get("final_title") or "")[:46]
        logger.info(f"  [skip {n}] 관련 없음 저장(id={row['id']}): {title}")
        return

    rid = save_refined_output(row["id"], result, model)
    with _lock:
        _counters["refined"] += 1
        n = _counters["refined"]
    logger.info(f"  [{n}] 완료(id={rid}): {result['final_title'][:46]}")


def run(
    workers: int,
    min_score: float,
    shard: str,
    limit: int | None,
    cost_every: int,
    text_gate: bool = True,
    triage_limit: int = 0,
) -> int:
    shard_i, shard_n = _parse_shard(shard)
    cid = str(uuid.uuid4())[:8]
    logger = HarnessLogger(tier=3, correlation_id=cid)
    logger.info(
        f"=== edu Tier3 병렬 정제 (run_id={cid}, workers={workers}, shard={shard}, "
        f"text_gate={text_gate}, triage_limit={triage_limit}) ==="
    )

    _triage_rule_skips(min_score, shard_i, shard_n, triage_limit, logger)

    rows = _fetch_candidates(min_score, shard_i, shard_n, limit, text_gate=text_gate)
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
    ap.add_argument("--triage-limit", type=int, default=0,
                    help="LLM 호출 전 rule-skip으로 폐기 저장할 최대 건수 (기본 0)")
    ap.add_argument("--free-tier", action="store_true",
                    help="GEMINI_API_KEY_FREE 키 사용 (무료 티어). workers 2로 고정, 비용 게이트 우회.")
    ap.add_argument("--no-text-gate", action="store_true",
                    help="AI/디지털 교육 텍스트 게이트를 끄고 모든 edu 후보를 처리합니다.")
    args = ap.parse_args()

    if args.free_tier:
        free_key = os.getenv("GEMINI_API_KEY_FREE", "").strip()
        if not free_key:
            print("ERROR: --free-tier 사용 시 .env에 GEMINI_API_KEY_FREE 설정 필요", flush=True)
            sys.exit(1)
        os.environ["GOOGLE_API_KEY"] = free_key
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ["API_COST_SOURCE"] = "gemini-free-tier"
        # 무료 티어 과금 없음 → 비용 게이트를 사실상 비활성화
        os.environ["DAILY_COST_LIMIT_USD"] = "9999"
        globals()["DAILY_COST_LIMIT"] = 9999.0
        # 무료 티어 RPM(10) 초과 방지 — workers 2 이하로 제한
        workers = min(args.workers, 2)
        print(f"[free-tier] GEMINI_API_KEY_FREE 적용, workers={workers}", flush=True)
    else:
        workers = args.workers

    run(
        workers,
        args.min_score,
        args.shard,
        args.limit,
        args.cost_every,
        text_gate=not args.no_text_gate,
        triage_limit=args.triage_limit,
    )
