#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
RESET_STATUS_PATH = ROOT / "docs" / "reports" / "paper_trading_reset_status.json"


def _run(cmd: list[str]) -> None:
    completed = subprocess.run(cmd, cwd=ROOT)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _reset_pending() -> bool:
    if not RESET_STATUS_PATH.exists():
        return False
    try:
        payload = __import__("json").loads(RESET_STATUS_PATH.read_text())
        return bool(payload.get("reset_pending")) and not bool(payload.get("flat"))
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh evidence-driven trading universe, then run broker trader.")
    parser.add_argument("--broker", choices=["alpaca", "ibkr"], required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--domain", default="physical_ai")
    parser.add_argument("--lookback-days", type=int, default=45)
    parser.add_argument("--max-symbols", type=int, default=24)
    parser.add_argument("--filter-limit", type=int, default=None)
    args = parser.parse_args()

    if _reset_pending():
        print('{"status":"blocked","reason":"paper_trading_reset_pending"}')
        return 2

    build_cmd = [
        str(PYTHON),
        "scripts/build_trading_universe.py",
        "--refresh-pipeline",
        "--domain",
        args.domain,
        "--lookback-days",
        str(args.lookback_days),
        "--max-symbols",
        str(args.max_symbols),
    ]
    if args.filter_limit is not None:
        build_cmd.extend(["--filter-limit", str(args.filter_limit)])
    _run(build_cmd)

    trader_script = "scripts/turtle_auto_trader.py" if args.broker == "alpaca" else "scripts/ibkr_tws_paper_trader.py"
    trader_cmd = [str(PYTHON), trader_script]
    if args.execute:
        trader_cmd.append("--execute")
    _run(trader_cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
