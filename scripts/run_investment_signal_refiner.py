"""
Investment Signal Refiner — daily Turtle Trading candidate preparation.

This replaces the publication-oriented Tier 2 content filter in the pipeline UI.
It does not place orders. It prepares a once-per-day watchlist from daily bars so
the CEO can see which symbols are candidates, already tracked, or simply on watch.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from scripts.alpaca_paper_trading import (  # noqa: E402
    TURTLE_RISK_PCT,
    TURTLE_S1_ENTRY,
    TURTLE_S2_ENTRY,
    get_account_summary,
    get_positions,
    get_turtle_signal,
)
from scripts.turtle_auto_trader import (  # noqa: E402
    MAX_POSITIONS,
    STATE_PATH,
    UNIVERSE,
    load_state,
    turtle_gate_check,
)

DEFAULT_OUTPUT = ROOT / "docs/reports/investment_signal_candidates.json"
DEFAULT_AUDIT_LOG = ROOT / "docs/reports/investment_signal_candidates.jsonl"

SYMBOL_NAMES = {
    "GOOG": "Google",
    "GOOGL": "Google",
    "GOOP": "Google",
    "NVDA": "NVIDIA",
    "TER": "Teradyne",
    "TSLA": "Tesla",
    "SMH": "Semiconductor ETF",
    "SOXX": "Semiconductor ETF",
    "BOTZ": "Robotics ETF",
    "PLTR": "Palantir",
    "ROBO": "Robotics ETF",
    "SPY": "S&P 500 ETF",
    "QQQ": "Nasdaq 100 ETF",
}

CATEGORY_LABELS = {
    "entry_candidate": "신규 매수 검토",
    "entry_blocked": "진입 조건 미충족",
    "exit_candidate": "매도/청산 검토",
    "tracked_hold": "규칙대로 보유 중",
    "manual_position": "수동 보유 종목",
    "watch": "관망",
    "data_unavailable": "데이터 부족",
}

ACTION_LABELS = {
    "prepare_paper_entry_review": "Paper 주문 검토 자료 준비",
    "do_not_enter": "진입하지 않음",
    "review_paper_exit": "Paper 청산 검토",
    "hold_and_monitor": "보유하고 손절가/청산 신호만 점검",
    "review_outside_turtle_state": "Turtle 추적 대상인지 별도 확인",
    "no_trade_signal_today": "오늘 일봉 기준 신호 없음",
    "skip": "건너뜀",
}

REASON_LABELS = {
    "already_tracked_by_turtle_state": "이미 Turtle 규칙으로 추적 중",
    "alpaca_position_exists_but_not_tracked_by_turtle_state": "계좌에는 있으나 Turtle 자동 추적 대상은 아님",
    "no_daily_breakout_or_exit_signal": "오늘 일봉 기준 신규 진입/청산 신호 없음",
    "daily_breakout_signal": "일봉 돌파 신호 발생",
    "max_positions_reached": "최대 보유 종목 수 도달",
    "turtle_gate_failed": "Turtle 필수 조건 미충족",
    "daily_bar_history_insufficient": "일봉 이력이 부족함",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _reason_label(reason: str | None) -> str | None:
    if not reason:
        return None
    return REASON_LABELS.get(reason, reason)


def _parse_universe(value: str | None) -> list[str]:
    raw = value or ",".join(UNIVERSE)
    symbols = []
    for item in raw.split(","):
        symbol = item.strip().upper()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def _position_map(positions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(pos.get("symbol", "")).upper(): pos
        for pos in positions
        if pos.get("symbol") and "error" not in pos
    }


def _exit_status(symbol: str, signal: dict[str, Any], tracked: dict[str, Any] | None, position: dict[str, Any] | None) -> dict[str, Any]:
    if not tracked:
        return {"exit_candidate": False, "exit_reason": None}

    current_price = float(signal.get("current_price") or position.get("current_price") or 0) if position else float(signal.get("current_price") or 0)
    stop_loss = tracked.get("stop_loss") or (position or {}).get("stop_loss")
    if stop_loss and current_price and current_price < float(stop_loss):
        return {
            "exit_candidate": True,
            "exit_reason": f"price_below_stop_loss ({current_price:.2f} < {float(stop_loss):.2f})",
        }

    system = tracked.get("system")
    if system == "S1" and signal.get("current_price") and signal.get("s1_low"):
        if float(signal["current_price"]) < float(signal["s1_low"]):
            return {
                "exit_candidate": True,
                "exit_reason": f"price_below_{TURTLE_S1_ENTRY}d_low",
            }
    if system == "S2" and signal.get("current_price") and signal.get("s2_low"):
        if float(signal["current_price"]) < float(signal["s2_low"]):
            return {
                "exit_candidate": True,
                "exit_reason": f"price_below_{TURTLE_S2_ENTRY}d_low",
            }

    return {"exit_candidate": False, "exit_reason": None}


def _classify(
    symbol: str,
    signal: dict[str, Any],
    account_value: float,
    positions_by_symbol: dict[str, dict[str, Any]],
    state: dict[str, Any],
) -> dict[str, Any]:
    tracked = state.get("turtle_positions", {}).get(symbol)
    position = positions_by_symbol.get(symbol)
    common = {
        "symbol": symbol,
        "name": SYMBOL_NAMES.get(symbol, symbol),
        "signal": signal.get("signal"),
        "system": signal.get("system"),
        "direction": signal.get("direction"),
        "current_price": signal.get("current_price"),
        "atr": signal.get("atr"),
        "as_of": signal.get("as_of"),
        "s1_high": signal.get("s1_high"),
        "s1_low": signal.get("s1_low"),
        "s2_high": signal.get("s2_high"),
        "s2_low": signal.get("s2_low"),
        "tracked": bool(tracked),
        "position_qty": position.get("qty") if position else None,
    }

    if signal.get("signal") in {"insufficient_data", "error"}:
        return {
            **common,
            "category": "data_unavailable",
            "action": "skip",
            "reason": signal.get("error") or "daily_bar_history_insufficient",
            "reason_label": _reason_label(signal.get("error") or "daily_bar_history_insufficient"),
            "rank": 90,
        }

    exit_info = _exit_status(symbol, signal, tracked, position)
    if exit_info["exit_candidate"]:
        return {
            **common,
            **exit_info,
            "category": "exit_candidate",
            "action": "review_paper_exit",
            "reason": exit_info["exit_reason"],
            "reason_label": _reason_label(exit_info["exit_reason"]),
            "rank": 5,
        }

    if tracked:
        return {
            **common,
            **exit_info,
            "category": "tracked_hold",
            "action": "hold_and_monitor",
            "reason": "already_tracked_by_turtle_state",
            "reason_label": _reason_label("already_tracked_by_turtle_state"),
            "stop_loss": tracked.get("stop_loss"),
            "entry_price": tracked.get("entry_price"),
            "rank": 30,
        }

    if position:
        return {
            **common,
            **exit_info,
            "category": "manual_position",
            "action": "review_outside_turtle_state",
            "reason": "alpaca_position_exists_but_not_tracked_by_turtle_state",
            "reason_label": _reason_label("alpaca_position_exists_but_not_tracked_by_turtle_state"),
            "entry_price": position.get("entry_price"),
            "rank": 40,
        }

    if signal.get("signal") in {"breakout_long", "breakout_short"}:
        gate = turtle_gate_check(signal, account_value)
        maxed = len(state.get("turtle_positions", {})) >= MAX_POSITIONS
        category = "entry_candidate" if gate["passed"] and not maxed else "entry_blocked"
        return {
            **common,
            **exit_info,
            "category": category,
            "action": "prepare_paper_entry_review" if category == "entry_candidate" else "do_not_enter",
            "reason": "daily_breakout_signal" if category == "entry_candidate" else ("max_positions_reached" if maxed else "turtle_gate_failed"),
            "reason_label": _reason_label("daily_breakout_signal" if category == "entry_candidate" else ("max_positions_reached" if maxed else "turtle_gate_failed")),
            "shares": gate.get("shares"),
            "stop_loss": gate.get("stop_loss"),
            "risk_pct": gate.get("risk_pct"),
            "position_value": gate.get("position_value"),
            "turtle_gate": gate,
            "rank": 10 if signal.get("system") == "S2" else 15,
        }

    return {
        **common,
        **exit_info,
        "category": "watch",
        "action": "no_trade_signal_today",
        "reason": "no_daily_breakout_or_exit_signal",
        "reason_label": _reason_label("no_daily_breakout_or_exit_signal"),
        "rank": 70,
    }


def refine(universe: list[str]) -> dict[str, Any]:
    generated_at = now_iso()
    state = load_state()
    state.setdefault("turtle_positions", {})

    account = get_account_summary()
    if not account.get("ok"):
        raise RuntimeError(f"account_lookup_failed: {account.get('error')}")
    account_value = float(account.get("portfolio_value") or 0)

    positions = get_positions()
    positions_by_symbol = _position_map(positions)
    scan_symbols = list(universe)
    for symbol in sorted(set(positions_by_symbol) | set(state.get("turtle_positions", {}))):
        if symbol not in scan_symbols:
            scan_symbols.append(symbol)

    items = []
    for symbol in scan_symbols:
        signal = get_turtle_signal(symbol)
        items.append(_classify(symbol, signal, account_value, positions_by_symbol, state))

    items.sort(key=lambda item: (item["rank"], item["symbol"]))
    summary = {
        "entry_candidates": sum(1 for item in items if item["category"] == "entry_candidate"),
        "entry_blocked": sum(1 for item in items if item["category"] == "entry_blocked"),
        "exit_candidates": sum(1 for item in items if item["category"] == "exit_candidate"),
        "tracked_holds": sum(1 for item in items if item["category"] == "tracked_hold"),
        "manual_positions": sum(1 for item in items if item["category"] == "manual_position"),
        "watch": sum(1 for item in items if item["category"] == "watch"),
        "data_unavailable": sum(1 for item in items if item["category"] == "data_unavailable"),
    }

    return {
        "generated_at": generated_at,
        "purpose": "daily_turtle_trading_data_refinement",
        "not_investment_advice": True,
        "execution_policy": "data_refinement_only_no_orders",
        "daily_bar_policy": "uses 1Day bars; intended to run once per trading day",
        "state_path": str(STATE_PATH.relative_to(ROOT)),
        "universe": universe,
        "scanned_symbols": scan_symbols,
        "account": {
            "portfolio_value": account.get("portfolio_value"),
            "cash": account.get("cash"),
            "status": account.get("status"),
        },
        "rules": {
            "s1_entry_days": TURTLE_S1_ENTRY,
            "s2_entry_days": TURTLE_S2_ENTRY,
            "risk_per_position_pct": TURTLE_RISK_PCT * 100,
            "max_positions": MAX_POSITIONS,
        },
        "summary": summary,
        "items": items,
    }


def write_outputs(report: dict[str, Any], output: Path, audit_log: Path | None, dry_run: bool) -> None:
    if dry_run:
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if audit_log:
        audit_log.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "generated_at": report["generated_at"],
                "summary": report["summary"],
                "output": str(output.relative_to(ROOT)),
            }, ensure_ascii=False) + "\n")


def print_summary(report: dict[str, Any], output: Path, dry_run: bool) -> None:
    summary = report["summary"]
    print("투자 신호 정제 — 일봉 기준 Turtle Trading 후보 정리")
    print(f"generated_at={report['generated_at']}")
    print("기준=1Day 일봉, 하루 1회 실행")
    print("실행정책=자료 정제만 수행, 주문 없음")
    print(
        "요약="
        f"신규 매수 검토:{summary['entry_candidates']} "
        f"매도/청산 검토:{summary['exit_candidates']} "
        f"규칙대로 보유:{summary['tracked_holds']} "
        f"수동 보유:{summary['manual_positions']} "
        f"관망:{summary['watch']} "
        f"조건 미충족:{summary['entry_blocked']} "
        f"데이터 부족:{summary['data_unavailable']}"
    )
    for item in report["items"]:
        price = item.get("current_price")
        system = item.get("system") or "-"
        category = CATEGORY_LABELS.get(item["category"], item["category"])
        action = ACTION_LABELS.get(item["action"], item["action"])
        print(
            f"- {item['symbol']} ({item['name']}): {category} | "
            f"{action} | 신호={item.get('signal')} {system} | 가격={price} | 사유={item.get('reason_label')}"
        )
    if dry_run:
        print("테스트 실행=true; 보고서 파일은 저장하지 않음")
    else:
        print(f"output={output.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily investment signal refinement from Turtle Trading rules")
    parser.add_argument("--universe", default=os.getenv("PAPER_TRADING_UNIVERSE"), help="Comma-separated symbols")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-log", type=Path, default=DEFAULT_AUDIT_LOG)
    parser.add_argument("--dry-run", action="store_true", help="Print only; do not write report files")
    args = parser.parse_args()

    report = refine(_parse_universe(args.universe))
    write_outputs(report, args.output, args.audit_log, args.dry_run)
    print_summary(report, args.output, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
