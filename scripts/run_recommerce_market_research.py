#!/usr/bin/env python3
"""Refresh conservative local-LLM OJT targets from Naver price evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

from core.recommerce_market_research import run_market_research  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "runtime/recommerce/market_research.json")
    args = parser.parse_args()
    result = run_market_research(args.output)
    print(json.dumps({
        "status": result["status"],
        "observed_at": result["observed_at"],
        "candidate_count": len(result["candidates"]),
        "candidate_ids": [item["id"] for item in result["candidates"]],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
