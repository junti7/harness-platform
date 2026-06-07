#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from ib_insync import IB  # noqa: E402
from scripts.alpaca_paper_trading import _trading_get, get_positions  # noqa: E402

STATUS_PATH = ROOT / "docs" / "reports" / "paper_trading_reset_status.json"
ALPACA_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.harness.turtle-auto-trader.plist"
AUTO_RESUME_AFTER_RESET = os.getenv("PAPER_TRADING_AUTO_RESUME_AFTER_RESET", "false").strip().lower() == "true"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ny_market_context() -> dict:
    from zoneinfo import ZoneInfo
    now_ny = datetime.now(ZoneInfo("America/New_York"))
    hhmm = now_ny.hour * 100 + now_ny.minute
    is_weekday = now_ny.weekday() < 5
    market_open = is_weekday and 930 <= hhmm < 1600
    return {
        "now_ny": now_ny.isoformat(timespec="seconds"),
        "market_open": market_open,
        "session": "regular" if market_open else "closed",
    }


def read_status() -> dict:
    if STATUS_PATH.exists():
        try:
            return json.loads(STATUS_PATH.read_text())
        except Exception:
            pass
    return {}


def write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))


def check_alpaca() -> dict:
    open_orders = _trading_get("/orders", {"status": "open", "limit": 50, "direction": "desc"})
    positions = [p for p in get_positions() if "symbol" in p]
    return {
        "open_orders": [(o.get("symbol"), o.get("side"), o.get("status"), o.get("qty")) for o in open_orders],
        "positions": [(p["symbol"], p["qty"]) for p in positions],
        "flat": not open_orders and not positions,
    }


def check_ibkr() -> dict:
    port = 4002 if os.getenv("IBKR_TRADING_MODE", "paper").strip().lower() == "paper" else 4001
    ib = IB()
    ib.connect("127.0.0.1", port, clientId=101, timeout=10)
    try:
        open_orders = [(t.order.orderId, t.contract.symbol, t.order.action, t.orderStatus.status, t.order.totalQuantity) for t in ib.reqAllOpenOrders()]
        positions = [(p.contract.symbol, p.position, p.contract.exchange, p.contract.currency) for p in ib.positions()]
        return {"open_orders": open_orders, "positions": positions, "flat": not open_orders and not positions}
    finally:
        ib.disconnect()


def maybe_resume_alpaca_scheduler() -> str:
    if not ALPACA_PLIST.exists():
        return "plist_missing"
    completed = subprocess.run(["launchctl", "load", str(ALPACA_PLIST)], capture_output=True, text=True)
    return "loaded" if completed.returncode == 0 else f"load_failed:{completed.stderr.strip()[:200]}"


def main() -> int:
    status = read_status()
    alpaca = check_alpaca()
    ibkr = check_ibkr()
    flat = alpaca["flat"] and ibkr["flat"]
    result = {
        "checked_at": now_iso(),
        "reset_pending": bool(status.get("reset_pending")),
        "alpaca": alpaca,
        "ibkr": ibkr,
        "flat": flat,
        "market_context": ny_market_context(),
    }
    if not flat:
        if not result["market_context"]["market_open"]:
            result["next_action"] = "미국장 종료 상태입니다. Alpaca accepted / IBKR PreSubmitted 청산 주문은 다음 미국 정규장 개장 후 체결 대기입니다."
        else:
            result["next_action"] = "미국장 개장 중입니다. 미체결 청산 주문과 잔존 포지션을 계속 감시합니다."
    if status.get("reset_pending"):
        result["reset_pending"] = not flat
        if flat:
            result["resume_alpaca_scheduler"] = maybe_resume_alpaca_scheduler() if AUTO_RESUME_AFTER_RESET else "disabled"
    write_status({**status, **result})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
