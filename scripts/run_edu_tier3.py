#!/usr/bin/env python3
"""
edu_consulting 도메인 전용 Tier 3 정제 러너.

기본 refine()은 score DESC 정렬이라 physical_ai(0.8대)가 배치를 먼저 채워
edu_consulting(0.1~0.4) 항목이 정제되지 않는다. 이 러너는 edu만 골라 정제해
상담사 근거 뱅크(evidence_bank.json)의 'fresh_pipeline' 항목을 채운다.

정제 후 refresh_edu_evidence_bank로 뱅크를 즉시 갱신한다.

사용:
  python scripts/run_edu_tier3.py --limit 10
  python scripts/run_edu_tier3.py --limit 5 --min-score 0.2
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
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
    _error_skipped_output,
    get_today_cost,
    DEFAULT_GEMINI_MODEL,
    DAILY_COST_LIMIT,
)


def run(limit: int, min_score: float) -> int:
    cid = str(uuid.uuid4())[:8]
    logger = HarnessLogger(tier=3, correlation_id=cid)
    logger.info(f"=== edu_consulting Tier 3 정제 시작 (run_id={cid}) ===")

    rows = execute_query("""
        SELECT fs.id, fs.title, fs.summary, fs.content_hash, fs.source, fs.score,
               fs.extracted_facts, 'edu_consulting' AS domain
        FROM filtered_signals fs
        LEFT JOIN refined_outputs ro ON fs.id = ro.filtered_signal_id
        WHERE ro.id IS NULL
          AND fs.domain = 'edu_consulting'
          AND fs.score >= %s
        ORDER BY fs.score DESC
        LIMIT %s
    """, (min_score, limit), fetch=True) or []

    if not rows:
        logger.info("정제 대상 edu_consulting 항목 없음")
        return 0

    logger.info(f"정제 대상: {len(rows)}개 (min_score={min_score})")
    model = DEFAULT_GEMINI_MODEL
    refined = skipped = 0

    for i, row in enumerate(rows):
        if get_today_cost(logger) >= DAILY_COST_LIMIT:
            logger.warning("일일 비용 한도 도달 — 중단")
            break
        logger.info(f"[{i+1}/{len(rows)}] {row['title'][:50]}... (score={row['score']:.2f})")
        try:
            result = refine_signal(model, dict(row))
        except Exception as e:
            fb = _fallback_refined_output(dict(row), e)
            if fb:
                save_refined_output(row["id"], fb, f"{model}:fallback")
                logger.warning(f"  {type(e).__name__} — fallback 저장")
                refined += 1
            else:
                skipped_output = _error_skipped_output(dict(row), e)
                save_refined_output(row["id"], skipped_output, f"{model}:error-skip")
                logger.warning(f"  오류 탈락 저장: {type(e).__name__}: {e}")
                skipped += 1
            continue

        if not result.get("is_relevant", True):
            save_refined_output(row["id"], result, f"{model}:irrelevant")
            logger.info("  → 관련 없음, 탈락")
            skipped += 1
            continue

        rid = save_refined_output(row["id"], result, model)
        logger.info(f"  → 완료(id={rid}): {result['final_title'][:50]}")
        refined += 1

    logger.info(f"=== edu Tier 3 완료: 정제 {refined} / 스킵 {skipped} ===")

    # 근거 뱅크 즉시 갱신
    try:
        from scripts.refresh_edu_evidence_bank import build_bank, BANK_PATH
        bank = build_bank(window_days=45, max_fresh=25)
        if bank["_meta"]["counts"]["total"] > 0:
            BANK_PATH.write_text(json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
            c = bank["_meta"]["counts"]
            logger.info(f"[근거 뱅크] 갱신: 총 {c['total']} (앵커 {c['evergreen_anchors']} + 최신 {c['fresh_pipeline']})")
    except Exception as e:
        logger.warning(f"[근거 뱅크] 갱신 실패: {e}")

    return refined


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="edu_consulting 전용 Tier 3 정제")
    ap.add_argument("--limit", type=int, default=10, help="정제 최대 건수 (기본 10)")
    ap.add_argument("--min-score", type=float, default=0.1, help="최소 점수 (기본 0.1)")
    args = ap.parse_args()
    raise SystemExit(0 if run(args.limit, args.min_score) >= 0 else 1)
