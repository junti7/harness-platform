#!/usr/bin/env python3
"""seed에 없는 투자 후보 회사를 evidence에서 발굴해 제안 큐로 출력.

발굴은 자동, 편입은 게이트(legal_review_approve + red_team_clear + 대표 승인). 거래/seed 변경 없음.

사용:
  PYTHONPATH=. .venv/bin/python scripts/mine_universe_candidates.py
  PYTHONPATH=. .venv/bin/python scripts/mine_universe_candidates.py --lookback-days 45 --min-sources 3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.universe_candidate_miner import mine_candidates, write_candidate_queue  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Mine unmatched investment candidates from evidence.")
    ap.add_argument("--domain", default="physical_ai")
    ap.add_argument("--lookback-days", type=int, default=30)
    ap.add_argument("--min-sources", type=int, default=2, help="distinct source 최소(단일소스 스팸 차단)")
    ap.add_argument("--max-candidates", type=int, default=25)
    ap.add_argument("--max-evidence", type=int, default=400, help="LLM 비용 상한용 evidence 캡")
    args = ap.parse_args()

    candidates = mine_candidates(
        domain=args.domain,
        lookback_days=args.lookback_days,
        min_sources=args.min_sources,
        max_candidates=args.max_candidates,
        max_evidence=args.max_evidence,
    )
    write_candidate_queue(candidates, args.domain, args.lookback_days, args.min_sources)
    print(json.dumps({
        "domain": args.domain,
        "candidate_count": len(candidates),
        "top": [
            {"name": c["name"], "ticker": c["ticker_guess"], "distinct_sources": c["distinct_sources"]}
            for c in candidates[:10]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
