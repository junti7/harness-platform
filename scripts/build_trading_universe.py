#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.content.filter import filter_signals  # noqa: E402
from adapters.content.signalizer import promote_signals  # noqa: E402
from core.trading_universe import build_trading_universe, ensure_trading_db_url, now_iso, write_trading_universe  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dynamic trading universe from filtered physical_ai evidence.")
    parser.add_argument("--domain", default="physical_ai")
    parser.add_argument("--lookback-days", type=int, default=45)
    parser.add_argument("--max-symbols", type=int, default=24)
    parser.add_argument("--refresh-pipeline", action="store_true", help="Run Tier2 filter + signal promotion before universe build")
    parser.add_argument("--filter-limit", type=int, default=None)
    parser.add_argument("--skip-ko", action="store_true", help="Skip Korean translation enrichment for fast runtime rebuilds")
    args = parser.parse_args()
    ensure_trading_db_url()

    if args.refresh_pipeline:
        filter_signals(correlation_id="trading-universe-refresh", limit=args.filter_limit, domain=args.domain)
        promote_signals(correlation_id="trading-universe-refresh", domain=args.domain)

    universe = build_trading_universe(
        domain=args.domain,
        lookback_days=args.lookback_days,
        max_symbols=args.max_symbols,
        translate_reasons=not args.skip_ko,
    )
    write_trading_universe(universe)

    payload = {
        "generated_at": now_iso(),
        "domain": args.domain,
        "symbol_count": len(universe),
        "symbols": [row["symbol"] for row in universe],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
