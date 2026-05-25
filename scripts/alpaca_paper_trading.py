"""
Alpaca Paper Trading — Turtle Trading Simulation Engine
AR-018 조건5: 8주 Paper Trading 선행 프로토콜
"""

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

ALPACA_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets/v2").rstrip("/")
ALPACA_DATA_URL = "https://data.alpaca.markets/v2"

TURTLE_S1_ENTRY = 20
TURTLE_S2_ENTRY = 55
TURTLE_ATR_PERIOD = 20
TURTLE_STOP_MULT = 2
TURTLE_RISK_PCT = 0.01

SIGNAL_UNIVERSE = ["NVDA", "SMH", "SOXX", "BOTZ", "TSLA", "PLTR", "ROBO", "SPY"]
INITIAL_CAPITAL = 100_000.0

_HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
}


def _trading_get(path: str, params: dict | None = None) -> Any:
    url = f"{ALPACA_BASE_URL}/{path.lstrip('/')}"
    r = requests.get(url, headers=_HEADERS, params=params or {}, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Alpaca {r.status_code}: {r.text[:300]}")
    return r.json()


def _data_get(path: str, params: dict | None = None) -> Any:
    url = f"{ALPACA_DATA_URL}/{path.lstrip('/')}"
    r = requests.get(url, headers=_HEADERS, params=params or {}, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Alpaca Data {r.status_code}: {r.text[:300]}")
    return r.json()


def get_account_summary() -> dict[str, Any]:
    try:
        a = _trading_get("/account")
        pv = float(a.get("portfolio_value") or 0)
        eq = float(a.get("equity") or 0)
        cash = float(a.get("cash") or 0)
        bp = float(a.get("buying_power") or 0)
        total_pnl = pv - INITIAL_CAPITAL
        return {
            "ok": True,
            "account_id": (a.get("id") or "")[:8] + "...",
            "status": a.get("status"),
            "portfolio_value": round(pv, 2),
            "equity": round(eq, 2),
            "cash": round(cash, 2),
            "buying_power": round(bp, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl / INITIAL_CAPITAL * 100, 3),
            "day_trade_count": a.get("daytrade_count", 0),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _get_bars(symbol: str, days: int = 70) -> list[dict]:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days + 40)
    try:
        data = _data_get(
            f"/stocks/{symbol}/bars",
            params={
                "timeframe": "1Day",
                "start": start.isoformat(),
                "end": end.isoformat(),
                "limit": 120,
                "adjustment": "all",
                "feed": "iex",
            },
        )
        bars = sorted(data.get("bars") or [], key=lambda b: b.get("t", ""))
        return bars[-days:] if len(bars) >= days else bars
    except Exception:
        return []


def _calc_atr(bars: list[dict], period: int = 20) -> float:
    if len(bars) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(bars)):
        h = float(bars[i].get("h", 0))
        lo = float(bars[i].get("l", 0))
        pc = float(bars[i - 1].get("c", 0))
        trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
    if len(trs) < period:
        return 0.0
    return round(sum(trs[-period:]) / period, 4)


def get_turtle_signal(symbol: str) -> dict[str, Any]:
    bars = _get_bars(symbol, days=70)
    if len(bars) < TURTLE_S2_ENTRY + 2:
        return {
            "symbol": symbol,
            "signal": "insufficient_data",
            "system": None,
            "direction": None,
            "current_price": 0,
            "atr": 0,
        }

    cp = float(bars[-1].get("c", 0))
    atr = _calc_atr(bars, TURTLE_ATR_PERIOD)

    s1_window = bars[-TURTLE_S1_ENTRY - 1 : -1]
    s2_window = bars[-TURTLE_S2_ENTRY - 1 : -1]
    s1_high = max(float(b.get("h", 0)) for b in s1_window)
    s1_low = min(float(b.get("l", 0)) for b in s1_window)
    s2_high = max(float(b.get("h", 0)) for b in s2_window)
    s2_low = min(float(b.get("l", 0)) for b in s2_window)

    signal, system, direction = "neutral", None, None
    if cp > s2_high:
        signal, system, direction = "breakout_long", "S2", "long"
    elif cp < s2_low:
        signal, system, direction = "breakout_short", "S2", "short"
    elif cp > s1_high:
        signal, system, direction = "breakout_long", "S1", "long"
    elif cp < s1_low:
        signal, system, direction = "breakout_short", "S1", "short"

    return {
        "symbol": symbol,
        "signal": signal,
        "direction": direction,
        "system": system,
        "current_price": round(cp, 2),
        "atr": round(atr, 4),
        "s1_high": round(s1_high, 2),
        "s1_low": round(s1_low, 2),
        "s2_high": round(s2_high, 2),
        "s2_low": round(s2_low, 2),
        "stop_long": round(cp - TURTLE_STOP_MULT * atr, 2) if atr > 0 else None,
        "stop_short": round(cp + TURTLE_STOP_MULT * atr, 2) if atr > 0 else None,
        "as_of": (bars[-1].get("t") or "")[:10],
        "bar_count": len(bars),
    }


def get_positions() -> list[dict[str, Any]]:
    try:
        raw = _trading_get("/positions")
        result = []
        for p in raw:
            sym = p.get("symbol", "")
            qty = float(p.get("qty") or 0)
            entry = float(p.get("avg_entry_price") or 0)
            cur = float(p.get("current_price") or 0)
            mv = float(p.get("market_value") or 0)
            pnl = float(p.get("unrealized_pl") or 0)
            pnl_pct = float(p.get("unrealized_plpc") or 0) * 100
            side = p.get("side", "long")

            bars = _get_bars(sym, days=25)
            atr = _calc_atr(bars, TURTLE_ATR_PERIOD) if len(bars) >= 21 else 0
            stop = round(entry - TURTLE_STOP_MULT * atr, 2) if atr > 0 and side == "long" else None

            result.append({
                "symbol": sym,
                "qty": qty,
                "side": side,
                "entry_price": round(entry, 2),
                "current_price": round(cur, 2),
                "market_value": round(mv, 2),
                "unrealized_pnl": round(pnl, 2),
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "atr": round(atr, 4),
                "stop_loss": stop,
                "near_stop": stop is not None and cur < stop * 1.03,
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]


def get_recent_orders(limit: int = 8) -> list[dict[str, Any]]:
    try:
        raw = _trading_get("/orders", params={"status": "all", "limit": limit, "direction": "desc"})
        result = []
        for o in raw:
            result.append({
                "id": str(o.get("id") or "")[:8],
                "symbol": o.get("symbol"),
                "side": o.get("side"),
                "type": o.get("type"),
                "qty": o.get("qty"),
                "filled_qty": o.get("filled_qty"),
                "fill_price": o.get("filled_avg_price"),
                "status": o.get("status"),
                "submitted_at": (o.get("submitted_at") or "")[:16].replace("T", " "),
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]


def get_portfolio_history() -> dict[str, Any]:
    try:
        h = _trading_get(
            "/account/portfolio/history",
            params={"period": "1M", "timeframe": "1D"},
        )
        equity = h.get("equity") or []
        timestamps = h.get("timestamp") or []
        pnl_pct = h.get("profit_loss_pct") or []

        chart = []
        for i, ts in enumerate(timestamps):
            chart.append({
                "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%m/%d"),
                "value": round(float(equity[i]) if i < len(equity) else 0, 2),
                "pnl_pct": round(float(pnl_pct[i]) * 100 if i < len(pnl_pct) else 0, 3),
            })
        return {"ok": True, "chart": chart, "base": float(h.get("base_value") or INITIAL_CAPITAL)}
    except Exception as e:
        return {"ok": False, "error": str(e), "chart": []}


def get_ar018_kpi(account: dict, positions: list) -> dict[str, Any]:
    total_pnl_pct = account.get("total_pnl_pct", 0)
    max_loss = min(
        (p.get("unrealized_pnl_pct", 0) for p in positions if "error" not in p),
        default=0.0,
    )
    return {
        "return_pct": round(total_pnl_pct, 3),
        "max_position_loss_pct": round(max_loss, 3),
        "max_loss_pass": max_loss > -15.0,
        "deposit_cap_usd": 500,
        "week_target": 8,
    }


def get_full_dashboard() -> dict[str, Any]:
    account = get_account_summary()
    positions = get_positions() if account.get("ok") else []
    signals = []
    for sym in SIGNAL_UNIVERSE:
        try:
            signals.append(get_turtle_signal(sym))
        except Exception as e:
            signals.append({"symbol": sym, "signal": "error", "error": str(e)})
    orders = get_recent_orders()
    history = get_portfolio_history()
    kpi = get_ar018_kpi(account, positions)
    active_signals = [s for s in signals if s.get("signal") not in ("neutral", "insufficient_data", "error")]

    return {
        "account": account,
        "positions": positions,
        "signals": signals,
        "active_signals": active_signals,
        "orders": orders,
        "history": history,
        "ar018_kpi": kpi,
        "universe": SIGNAL_UNIVERSE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
