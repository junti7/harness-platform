"""
Harness Trading Diary — 거래 일기장 모듈

매수/매도/신호/메모를 JSONL로 누적 기록한다.
turtle_auto_trader.py가 거래 시 자동 호출하고,
CEO가 수동 메모를 추가할 수 있다.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DIARY_PATH = ROOT / "docs/trading/trading_diary.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write(entry: dict[str, Any]) -> None:
    DIARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DIARY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


TICKER_NAMES: dict[str, str] = {
    "NVDA": "NVIDIA", "AVGO": "Broadcom", "TSM": "TSMC", "MU": "Micron",
    "ANET": "Arista Networks", "VRT": "Vertiv", "TER": "Teradyne",
    "CRWV": "CoreWeave", "SYM": "Symbotic", "ISRG": "Intuitive Surgical",
    "ROK": "Rockwell Automation", "PLTR": "Palantir", "TSLA": "Tesla",
    "CEG": "Constellation Energy", "VST": "Vistra Corp", "GEV": "GE Vernova",
    "PWR": "Quanta Services", "XYL": "Xylem", "ECL": "Ecolab",
    "VLTO": "Veralto", "QS": "QuantumScape", "STEM": "Stem Inc",
    "ALTM": "Arcadium Lithium", "ARM": "ARM Holdings",
}


def log_trade_entry(
    ticker: str,
    side: str,               # "buy" | "sell"
    shares: int,
    price: float,
    atr: float,
    stop_loss: float,
    system: str,             # "S1" | "S2"
    signal: str,             # "breakout_long" | "breakout_short"
    sector: str = "",
    harness_score: int = 0,
    selection_reason: str = "",
    note: str = "",
) -> str:
    entry_id = str(uuid.uuid4())[:8]
    entry = {
        "id": entry_id,
        "timestamp": _now(),
        "type": "trade_entry",
        "ticker": ticker,
        "company_name": TICKER_NAMES.get(ticker, ""),
        "side": side,
        "shares": shares,
        "price": round(price, 2),
        "position_value": round(shares * price, 2),
        "atr": round(atr, 4),
        "stop_loss": round(stop_loss, 2),
        "risk_usd": round(shares * atr, 2),
        "system": system,
        "signal": signal,
        "sector": sector,
        "harness_score": harness_score,
        "selection_reason": selection_reason,
        "pnl": None,
        "pnl_pct": None,
        "status": "open",
        "note": note,
    }
    _write(entry)
    return entry_id


def log_trade_exit(
    ticker: str,
    side: str,               # "sell" (long exit) | "buy" (short exit)
    shares: int,
    price: float,
    entry_price: float,
    exit_reason: str,        # "stop_loss" | "exit_signal_s1" | "exit_signal_s2" | "manual"
    note: str = "",
) -> str:
    entry_id = str(uuid.uuid4())[:8]
    pnl = round((price - entry_price) * shares, 2) if side == "sell" else round((entry_price - price) * shares, 2)
    pnl_pct = round((price - entry_price) / entry_price * 100, 3) if side == "sell" else round((entry_price - price) / entry_price * 100, 3)
    entry = {
        "id": entry_id,
        "timestamp": _now(),
        "type": "trade_exit",
        "ticker": ticker,
        "side": side,
        "shares": shares,
        "price": round(price, 2),
        "entry_price": round(entry_price, 2),
        "exit_reason": exit_reason,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "status": "closed",
        "note": note,
    }
    _write(entry)
    return entry_id


def log_signal_scan(results: list[dict], account_value: float) -> None:
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": _now(),
        "type": "signal_scan",
        "account_value": round(account_value, 2),
        "scanned_count": len(results),
        "breakout_count": sum(1 for r in results if "breakout" in r.get("signal", "")),
        "results": [
            {
                "ticker": r.get("ticker") or r.get("symbol"),
                "signal": r.get("signal"),
                "price": r.get("current_price"),
                "dist_to_s2_pct": r.get("dist_to_s2_pct"),
            }
            for r in results
        ],
    }
    _write(entry)


def log_ceo_note(
    note: str,
    ticker: str = "",
    tags: list[str] | None = None,
) -> str:
    entry_id = str(uuid.uuid4())[:8]
    entry = {
        "id": entry_id,
        "timestamp": _now(),
        "type": "ceo_note",
        "ticker": ticker,
        "note": note,
        "tags": tags or [],
    }
    _write(entry)
    return entry_id


def log_research_update(
    summary: str,
    new_tickers: list[str],
    sectors: list[str],
    source: str = "",
) -> str:
    entry_id = str(uuid.uuid4())[:8]
    entry = {
        "id": entry_id,
        "timestamp": _now(),
        "type": "research_update",
        "summary": summary,
        "new_tickers": new_tickers,
        "sectors": sectors,
        "source": source,
    }
    _write(entry)
    return entry_id


def load_diary(limit: int = 200) -> list[dict]:
    if not DIARY_PATH.exists():
        return []
    lines = DIARY_PATH.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    # 최신순 정렬
    entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return entries[:limit]


def diary_stats() -> dict:
    entries = load_diary(limit=10000)
    trades = [e for e in entries if e["type"] in ("trade_entry", "trade_exit")]
    exits  = [e for e in entries if e["type"] == "trade_exit"]
    total_pnl    = sum(e.get("pnl", 0) or 0 for e in exits)
    winning      = [e for e in exits if (e.get("pnl") or 0) > 0]
    win_rate     = round(len(winning) / len(exits) * 100, 1) if exits else 0
    return {
        "total_entries": len(entries),
        "total_trades":  len(trades),
        "closed_trades": len(exits),
        "win_rate_pct":  win_rate,
        "total_pnl":     round(total_pnl, 2),
    }
