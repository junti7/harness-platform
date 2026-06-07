#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from ib_insync import IB, MarketOrder, Stock  # noqa: E402
from scripts.alpaca_paper_trading import ALPACA_BASE_URL, ALPACA_KEY, ALPACA_SECRET, get_account_summary, get_positions  # noqa: E402

ALPACA_HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
    "Content-Type": "application/json",
}

IBKR_HOST = "127.0.0.1"
IBKR_PORT = 4002 if os.getenv("IBKR_TRADING_MODE", "paper").strip().lower() == "paper" else 4001
IBKR_CLIENT_ID = 91

ALPACA_STATE_PATH = ROOT / "docs" / "reports" / "paper_trading_positions.json"
IBKR_STATE_PATH = ROOT / "docs" / "reports" / "ibkr_tws_positions.json"
BACKUP_DIR = ROOT / "docs" / "reports" / "resets"
RESET_REPORT_PATH = ROOT / "docs" / "reports" / "paper_trading_reset_report.json"
RESET_STATUS_PATH = ROOT / "docs" / "reports" / "paper_trading_reset_status.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def backup_file(path: Path, tag: str) -> str | None:
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = BACKUP_DIR / f"{stamp}_{tag}_{path.name}"
    target.write_bytes(path.read_bytes())
    return str(target)


def reset_local_state() -> dict:
    ts = now_iso()
    alpaca_backup = backup_file(ALPACA_STATE_PATH, "alpaca")
    ibkr_backup = backup_file(IBKR_STATE_PATH, "ibkr")
    ALPACA_STATE_PATH.write_text(json.dumps({"turtle_positions": {}, "last_run": ts}, ensure_ascii=False, indent=2))
    IBKR_STATE_PATH.write_text(json.dumps({
        "positions": {},
        "pending_orders": {},
        "signal_alerts": {},
        "baseline": None,
        "nav_history": [],
        "last_run": ts,
    }, ensure_ascii=False, indent=2))
    return {"alpaca_backup": alpaca_backup, "ibkr_backup": ibkr_backup}


def alpaca_cancel_all_orders() -> int:
    r = requests.delete(f"{ALPACA_BASE_URL}/orders", headers=ALPACA_HEADERS, timeout=20)
    if not r.ok:
        raise RuntimeError(f"alpaca cancel orders failed: {r.status_code} {r.text[:300]}")
    try:
        payload = r.json() if r.text else []
        return len(payload) if isinstance(payload, list) else 0
    except Exception:
        return 0


def alpaca_close_position(symbol: str) -> dict:
    r = requests.delete(f"{ALPACA_BASE_URL}/positions/{symbol}", headers=ALPACA_HEADERS, timeout=20)
    body = r.text[:300]
    return {"symbol": symbol, "ok": r.status_code in (200, 204), "status": r.status_code, "body": body}


def reset_alpaca() -> dict:
    before = get_account_summary()
    positions = [p for p in get_positions() if "symbol" in p]
    cancelled = alpaca_cancel_all_orders()
    close_results = [alpaca_close_position(p["symbol"]) for p in positions]
    time.sleep(3)
    after_positions = [p for p in get_positions() if "symbol" in p]
    after = get_account_summary()
    return {
        "before": before,
        "cancelled_orders": cancelled,
        "positions_before": [p["symbol"] for p in positions],
        "close_results": close_results,
        "positions_after": [p["symbol"] for p in after_positions],
        "after": after,
    }


def _ibkr_contract_for_position(pos) -> Stock:
    c = pos.contract
    primary = getattr(c, "primaryExchange", "") or c.exchange or ""
    routing = "SMART"
    return Stock(c.symbol, routing, c.currency, primaryExchange=primary if routing != primary else "")


def reset_ibkr() -> dict:
    ib = IB()
    ib.connect(IBKR_HOST, IBKR_PORT, clientId=IBKR_CLIENT_ID, timeout=10)
    try:
        accounts = ib.managedAccounts()
        account = next((a for a in accounts if a.startswith("DU")), accounts[0] if accounts else "")
        nav_vals = ib.accountValues(account=account)
        nav_before = next((float(v.value) for v in nav_vals if v.tag == "NetLiquidation" and v.currency == "USD"), 0.0)
        cash_before = next((float(v.value) for v in nav_vals if v.tag == "TotalCashValue" and v.currency == "USD"), 0.0)

        open_trades = ib.openTrades()
        cancelled_ids = []
        for trade in open_trades:
            ib.cancelOrder(trade.order)
            cancelled_ids.append(trade.order.orderId)
        if cancelled_ids:
            ib.sleep(2)

        positions = ib.positions(account=account)
        close_orders = []
        for pos in positions:
            qty = abs(int(pos.position))
            if qty <= 0:
                continue
            action = "SELL" if pos.position > 0 else "BUY"
            contract = _ibkr_contract_for_position(pos)
            ib.qualifyContracts(contract)
            order = MarketOrder(action, qty)
            order.tif = "DAY"
            trade = ib.placeOrder(contract, order)
            close_orders.append({
                "symbol": contract.symbol,
                "qty": qty,
                "action": action,
                "order_id": trade.order.orderId,
            })
        if close_orders:
            ib.sleep(5)

        positions_after = ib.positions(account=account)
        nav_vals_after = ib.accountValues(account=account)
        nav_after = next((float(v.value) for v in nav_vals_after if v.tag == "NetLiquidation" and v.currency == "USD"), 0.0)
        cash_after = next((float(v.value) for v in nav_vals_after if v.tag == "TotalCashValue" and v.currency == "USD"), 0.0)
        return {
            "account": account,
            "nav_before": nav_before,
            "cash_before": cash_before,
            "cancelled_open_orders": cancelled_ids,
            "positions_before": [
                {"symbol": p.contract.symbol, "qty": float(p.position), "exchange": p.contract.exchange, "currency": p.contract.currency}
                for p in positions
            ],
            "close_orders": close_orders,
            "positions_after": [
                {"symbol": p.contract.symbol, "qty": float(p.position), "exchange": p.contract.exchange, "currency": p.contract.currency}
                for p in positions_after
            ],
            "nav_after": nav_after,
            "cash_after": cash_after,
        }
    finally:
        ib.disconnect()


def main() -> int:
    report = {
        "reset_at": now_iso(),
        "alpaca": reset_alpaca(),
        "ibkr": reset_ibkr(),
        "state_reset": reset_local_state(),
    }
    RESET_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    RESET_STATUS_PATH.write_text(json.dumps({
        "reset_pending": True,
        "reset_at": report["reset_at"],
        "flat": False,
    }, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
