#!/usr/bin/env python3
"""Daily paper trading health report.

Read-only by default. Use --repair-ibkr-stops only to restore missing IBKR
resident stop orders from the existing state file; it never opens new entries.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncio

try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

ROOT = Path(os.getenv("HARNESS_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

# Keep launchd lock policy authoritative over developer .env defaults.
load_dotenv(ROOT / ".env")

from ib_insync import IB, StopOrder  # noqa: E402

from core.atomic_io import update_json_atomic  # noqa: E402
from scripts import ibkr_tws_paper_trader as ibkr_trader  # noqa: E402
from scripts.alpaca_paper_trading import (  # noqa: E402
    _get_bars,
    _trading_get,
    get_account_summary,
    get_ar018_kpi,
    get_positions,
)


REPORT_PATH = ROOT / "docs/reports/paper_trading_health_report.json"
REPORT_LOG_PATH = ROOT / "docs/reports/paper_trading_health_report.jsonl"
ALPACA_STATE_PATH = ROOT / "docs/reports/paper_trading_positions.json"
IBKR_STATE_PATH = ROOT / "docs/reports/ibkr_tws_positions.json"

ACTIVE_ALPACA_ORDER_STATUSES = {"new", "accepted", "partially_filled", "pending_new"}
ACTIVE_IBKR_ORDER_STATUSES = {"Submitted", "PreSubmitted", "PendingSubmit", "ApiPending"}
BENCHMARKS = ["SPY", "QQQ", "SMH", "SOXX"]
ENTRY_LOCK_ALLOWED_SYMBOLS = {
    symbol.strip().upper()
    for symbol in os.getenv("PAPER_ENTRY_LOCK_ALLOWED_SYMBOLS", "ASX,TSM,VRT").split(",")
    if symbol.strip()
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
        return payload if isinstance(payload, dict) else {}
    except Exception as exc:  # noqa: BLE001
        return {"_read_error": str(exc)}


def write_report(payload: dict[str, Any]) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    REPORT_PATH.write_text(text + "\n")
    with REPORT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def collect_alpaca() -> dict[str, Any]:
    account = get_account_summary()
    positions = get_positions() if account.get("ok") else []
    orders_raw = _trading_get("/orders", {"status": "open", "limit": 100, "direction": "desc"})
    open_orders = [
        {
            "id": str(o.get("id") or ""),
            "symbol": o.get("symbol"),
            "side": o.get("side"),
            "type": o.get("type"),
            "qty": _float(o.get("qty")),
            "filled_qty": _float(o.get("filled_qty")),
            "status": o.get("status"),
            "stop_price": _float(o.get("stop_price"), 0.0) if o.get("stop_price") is not None else None,
        }
        for o in orders_raw
    ]
    state = load_json(ALPACA_STATE_PATH)
    active_positions = [p for p in positions if isinstance(p, dict) and "error" not in p]
    active_entry_orders = [
        order for order in open_orders
        if order.get("side") == "buy"
        and order.get("type") != "stop"
        and str(order.get("status") or "").lower() in ACTIVE_ALPACA_ORDER_STATUSES
    ]
    unexpected_positions = sorted(
        str(pos.get("symbol") or "").upper()
        for pos in active_positions
        if str(pos.get("symbol") or "").upper() not in ENTRY_LOCK_ALLOWED_SYMBOLS
    )
    missing_stops: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    for pos in active_positions:
        sym = str(pos.get("symbol") or "")
        qty = abs(_float(pos.get("qty")))
        stops = [
            o for o in open_orders
            if o.get("symbol") == sym
            and o.get("side") == "sell"
            and o.get("type") == "stop"
            and str(o.get("status") or "").lower() in ACTIVE_ALPACA_ORDER_STATUSES
        ]
        covered_qty = sum(_float(o.get("qty")) - _float(o.get("filled_qty")) for o in stops)
        ok = covered_qty >= qty and qty > 0
        row = {
            "symbol": sym,
            "position_qty": qty,
            "stop_count": len(stops),
            "covered_qty": round(covered_qty, 6),
            "ok": ok,
            "stop_prices": [o.get("stop_price") for o in stops],
            "state_tracked": sym in (state.get("turtle_positions") or {}),
        }
        coverage.append(row)
        if not ok:
            missing_stops.append(row)
    return {
        "ok": bool(account.get("ok")) and not missing_stops and not active_entry_orders and not unexpected_positions,
        "account": account,
        "positions": active_positions,
        "open_orders": open_orders,
        "stop_coverage": coverage,
        "missing_stops": missing_stops,
        "active_entry_orders": active_entry_orders,
        "entry_lock_allowed_symbols": sorted(ENTRY_LOCK_ALLOWED_SYMBOLS),
        "unexpected_positions_during_entry_lock": unexpected_positions,
        "state_error": state.get("_read_error"),
        "ar018_kpi": get_ar018_kpi(account, active_positions) if account.get("ok") else {},
    }


def connect_ibkr() -> IB:
    ib = IB()
    ib.connect(ibkr_trader.TWS_HOST, ibkr_trader.TWS_PORT, clientId=108, timeout=10)
    return ib


def _ibkr_open_orders(ib: IB) -> list[dict[str, Any]]:
    try:
        ib.reqAllOpenOrders()
        ib.sleep(1)
    except Exception:
        pass
    rows: list[dict[str, Any]] = []
    for tr in ib.openTrades():
        o = getattr(tr, "order", None)
        st = getattr(tr, "orderStatus", None)
        con = getattr(tr, "contract", None)
        if o is None:
            continue
        rows.append({
            "order_id": getattr(o, "orderId", None),
            "symbol": str(getattr(con, "symbol", "") or ""),
            "action": str(getattr(o, "action", "") or ""),
            "order_type": str(getattr(o, "orderType", "") or ""),
            "qty": _float(getattr(o, "totalQuantity", 0)),
            "filled_qty": _float(getattr(st, "filled", 0)) if st is not None else 0.0,
            "status": str(getattr(st, "status", "") or ""),
            "stop_price": _float(getattr(o, "auxPrice", 0), 0.0) or None,
        })
    return rows


def _repair_ibkr_stop(ib: IB, account: str, symbol: str, tracked: dict[str, Any], qty: int) -> int | None:
    stop_loss = normalize_stop_price(_float(tracked.get("stop_loss")), tracked)
    if stop_loss <= 0 or qty <= 0:
        return None
    contract = ibkr_trader.make_contract(symbol, tracked)
    ib.qualifyContracts(contract)
    order = StopOrder("SELL", qty, stop_loss)
    order.tif = "GTC"
    order.account = account
    trade = ib.placeOrder(contract, order)
    ib.sleep(1)
    return int(getattr(trade.order, "orderId", 0) or 0) or None


def normalize_stop_price(price: float, tracked: dict[str, Any]) -> float:
    """Normalize stop price to known broker tick sizes.

    KRX rejects non-tick prices (for example 2030881.4 KRW). For a protective
    sell stop, round down so the submitted stop is not above the strategy stop.
    """
    if price <= 0:
        return 0.0
    currency = str(tracked.get("currency") or "").upper()
    primary = str(tracked.get("primary_exchange") or tracked.get("exchange") or "").upper()
    if currency == "KRW" or primary in {"KRX", "KSE"}:
        if price >= 500_000:
            tick = 1_000
        elif price >= 100_000:
            tick = 500
        elif price >= 50_000:
            tick = 100
        elif price >= 10_000:
            tick = 50
        elif price >= 5_000:
            tick = 10
        elif price >= 1_000:
            tick = 5
        else:
            tick = 1
        return float(math.floor(price / tick) * tick)
    return round(price, 2)


def collect_ibkr(*, repair_stops: bool = False) -> dict[str, Any]:
    state = load_json(IBKR_STATE_PATH)
    if state.get("_read_error"):
        return {"ok": False, "state_error": state.get("_read_error")}

    try:
        ib = connect_ibkr()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "connect_error": str(exc), "missing_stops": ["ibkr_unreachable"]}
    repaired: list[dict[str, Any]] = []
    try:
        accounts = ib.managedAccounts()
        account = next((a for a in accounts if a.startswith("DU")), accounts[0] if accounts else "")
        nav_vals = ib.accountValues(account=account)
        nav = next((_float(v.value) for v in nav_vals if v.tag == "NetLiquidation" and v.currency == "USD"), None)
        cash = next((_float(v.value) for v in nav_vals if v.tag == "TotalCashValue" and v.currency == "USD"), None)
        portfolio = ib.portfolio(account=account)
        positions = [
            {
                "symbol": item.contract.symbol,
                "qty": _float(item.position),
                "avg_cost": _float(item.averageCost),
                "market_price": _float(item.marketPrice),
                "unrealized_pnl": _float(item.unrealizedPNL),
            }
            for item in portfolio
            if abs(_float(item.position)) > 0
        ]

        open_orders = _ibkr_open_orders(ib)
        tracked_positions = state.get("positions") or {}
        missing_stops: list[dict[str, Any]] = []
        coverage: list[dict[str, Any]] = []
        for pos in positions:
            sym = str(pos["symbol"])
            qty = abs(_float(pos.get("qty")))
            stops = [
                o for o in open_orders
                if o.get("symbol") == sym
                and str(o.get("action") or "").upper() == "SELL"
                and str(o.get("order_type") or "").upper() in {"STP", "STOP"}
                and str(o.get("status") or "") in ACTIVE_IBKR_ORDER_STATUSES
            ]
            covered_qty = sum(_float(o.get("qty")) - _float(o.get("filled_qty")) for o in stops)
            ok = covered_qty >= qty and qty > 0
            row = {
                "symbol": sym,
                "position_qty": qty,
                "stop_count": len(stops),
                "covered_qty": round(covered_qty, 6),
                "ok": ok,
                "stop_prices": [o.get("stop_price") for o in stops],
                "state_tracked": sym in tracked_positions,
                "state_stop_loss": (tracked_positions.get(sym) or {}).get("stop_loss"),
                "state_resident_stop_id": (tracked_positions.get(sym) or {}).get("resident_stop_id"),
            }
            if not ok and repair_stops and sym in tracked_positions:
                new_id = _repair_ibkr_stop(ib, account, sym, tracked_positions[sym], int(qty))
                if new_id:
                    submitted_price = normalize_stop_price(_float(tracked_positions[sym].get("stop_loss")), tracked_positions[sym])
                    repaired.append({
                        "symbol": sym,
                        "resident_stop_id": new_id,
                        "submitted_stop_price": submitted_price,
                    })
                    def _mutate(payload: dict[str, Any], sym: str = sym, new_id: int = new_id) -> None:
                        rec = payload.setdefault("positions", {}).setdefault(sym, {})
                        rec["resident_stop_id"] = new_id
                        rec["resident_stop_missing"] = False
                        rec["resident_stop_repaired_at"] = now_iso()
                        rec["resident_stop_submitted_price"] = normalize_stop_price(_float(rec.get("stop_loss")), rec)
                    update_json_atomic(IBKR_STATE_PATH, _mutate)
            coverage.append(row)
            if not ok:
                missing_stops.append(row)

        if repaired:
            open_orders = _ibkr_open_orders(ib)
            missing_stops = []
            coverage = []
            for pos in positions:
                sym = str(pos["symbol"])
                qty = abs(_float(pos.get("qty")))
                stops = [
                    o for o in open_orders
                    if o.get("symbol") == sym
                    and str(o.get("action") or "").upper() == "SELL"
                    and str(o.get("order_type") or "").upper() in {"STP", "STOP"}
                    and str(o.get("status") or "") in ACTIVE_IBKR_ORDER_STATUSES
                ]
                covered_qty = sum(_float(o.get("qty")) - _float(o.get("filled_qty")) for o in stops)
                ok = covered_qty >= qty and qty > 0
                row = {
                    "symbol": sym,
                    "position_qty": qty,
                    "stop_count": len(stops),
                    "covered_qty": round(covered_qty, 6),
                    "ok": ok,
                    "stop_prices": [o.get("stop_price") for o in stops],
                    "state_tracked": sym in tracked_positions,
                }
                coverage.append(row)
                if not ok:
                    missing_stops.append(row)

        tracked_syms = set((load_json(IBKR_STATE_PATH).get("positions") or {}).keys())
        broker_syms = {p["symbol"] for p in positions}
        return {
            "ok": not missing_stops and bool(account),
            "account": account,
            "nav": nav,
            "cash": cash,
            "positions": positions,
            "open_orders": open_orders,
            "stop_coverage": coverage,
            "missing_stops": missing_stops,
            "repaired_stops": repaired,
            "state_match": {
                "ok": tracked_syms == broker_syms,
                "only_broker": sorted(broker_syms - tracked_syms),
                "only_state": sorted(tracked_syms - broker_syms),
            },
        }
    finally:
        ib.disconnect()


def benchmark_snapshot() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for symbol in BENCHMARKS:
        try:
            bars = _get_bars(symbol, days=20)
            closes = [_float(b.get("c")) for b in bars if _float(b.get("c")) > 0]
            latest = closes[-1] if closes else None
            ret_10 = ((latest / closes[-11]) - 1) * 100 if latest and len(closes) >= 11 else None
            rows[symbol] = {
                "latest_close": round(latest, 4) if latest else None,
                "return_10_bars_pct": round(ret_10, 3) if ret_10 is not None else None,
            }
        except Exception as exc:  # noqa: BLE001
            rows[symbol] = {"error": str(exc)}
    return rows


def launchd_lock_status() -> dict[str, Any]:
    labels = {
        "alpaca": "com.harness.turtle-auto-trader",
        "ibkr": "com.harness.ibkr-auto-trader",
    }
    out: dict[str, Any] = {}
    uid = subprocess.run(["id", "-u"], capture_output=True, text=True, check=False).stdout.strip()
    for key, label in labels.items():
        try:
            completed = subprocess.run(
                ["launchctl", "print", f"gui/{uid}/{label}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            text = completed.stdout + completed.stderr
            out[key] = {
                "probe_ok": completed.returncode == 0,
                "max_positions_0": "PAPER_TRADING_MAX_POSITIONS => 0" in text,
                "pyramid_disabled": "PAPER_PYRAMID_ENABLED => false" in text,
                "auto_execute_false": "PAPER_TRADING_AUTO_EXECUTE => false" in text,
                "not_running": "state = not running" in text,
            }
        except Exception as exc:  # noqa: BLE001
            out[key] = {"probe_ok": False, "error": str(exc)}
    return out


def build_report(*, repair_ibkr_stops: bool = False) -> dict[str, Any]:
    alpaca = collect_alpaca()
    ibkr = collect_ibkr(repair_stops=repair_ibkr_stops)
    locks = launchd_lock_status()
    problems: list[str] = []
    if not alpaca.get("ok"):
        problems.append("alpaca_stop_or_account_health_failed")
    if alpaca.get("active_entry_orders"):
        problems.append("alpaca_active_entry_orders_during_lock")
    if alpaca.get("unexpected_positions_during_entry_lock"):
        problems.append("alpaca_unexpected_positions_during_lock")
    if not ibkr.get("ok"):
        problems.append("ibkr_stop_or_account_health_failed")
    if not (locks.get("alpaca", {}).get("max_positions_0") and locks.get("alpaca", {}).get("pyramid_disabled")):
        problems.append("alpaca_entry_lock_not_confirmed")
    if not (locks.get("ibkr", {}).get("max_positions_0") and locks.get("ibkr", {}).get("pyramid_disabled")):
        problems.append("ibkr_entry_lock_not_confirmed")
    return {
        "checked_at": now_iso(),
        "ok": not problems,
        "problems": problems,
        "repair_ibkr_stops": repair_ibkr_stops,
        "alpaca": alpaca,
        "ibkr": ibkr,
        "benchmarks": benchmark_snapshot(),
        "launchd_entry_lock": locks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily paper trading health report")
    parser.add_argument("--repair-ibkr-stops", action="store_true", help="Place missing IBKR stop orders from state stop_loss.")
    parser.add_argument("--json", action="store_true", help="Print compact JSON only.")
    args = parser.parse_args()

    report = build_report(repair_ibkr_stops=args.repair_ibkr_stops)
    write_report(report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
