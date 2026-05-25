"""
Turtle Auto Trader — Alpaca Paper Trading 자동화 파이프라인
AR-018 조건5: 8주 Paper Trading 선행 프로토콜

실행:
  python scripts/turtle_auto_trader.py            # dry-run (주문 없음)
  python scripts/turtle_auto_trader.py --execute  # 실제 paper 주문 실행
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── 환경 설정 ─────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

from scripts.alpaca_paper_trading import (
    ALPACA_KEY, ALPACA_SECRET, ALPACA_BASE_URL,
    TURTLE_STOP_MULT, TURTLE_ATR_PERIOD, TURTLE_RISK_PCT,
    get_account_summary, get_positions, get_turtle_signal,
    get_recent_orders, _get_bars, _calc_atr,
)

PAPER_AUTO_EXECUTE = os.getenv("PAPER_TRADING_AUTO_EXECUTE", "false").lower() == "true"
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "")

LOG_PATH = ROOT / "docs/reports/paper_trading_log.jsonl"
STATE_PATH = ROOT / "docs/reports/paper_trading_positions.json"

# Turtle Trading 유니버스 (Physical AI ETF 중심)
UNIVERSE = os.getenv(
    "PAPER_TRADING_UNIVERSE",
    "NVDA,SMH,SOXX,BOTZ,TSLA,PLTR,ROBO,QQQ"
).split(",")

MAX_POSITIONS = int(os.getenv("PAPER_TRADING_MAX_POSITIONS", "6"))

_HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
}


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_entry(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"turtle_positions": {}, "last_run": None}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _alpaca_post(path: str, body: dict) -> dict:
    url = f"{ALPACA_BASE_URL}/{path.lstrip('/')}"
    r = requests.post(url, headers={**_HEADERS, "Content-Type": "application/json"},
                      json=body, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Alpaca POST {r.status_code}: {r.text[:300]}")
    return r.json()


def _alpaca_delete(path: str) -> dict:
    url = f"{ALPACA_BASE_URL}/{path.lstrip('/')}"
    r = requests.delete(url, headers=_HEADERS, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Alpaca DELETE {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}


def post_slack(text: str) -> None:
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL:
        return
    try:
        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={"channel": SLACK_CHANNEL, "text": text},
            timeout=10,
        )
    except Exception:
        pass


# ── TurtleGate (Paper용 5항목 자동 검증) ─────────────────────────────────────

def turtle_gate_check(signal: dict, account_value: float) -> dict:
    """
    Paper Trading TurtleGate — 5항목 자동 검증
    항목 6(Pre-Mortem), 7(Cross-LLM)은 실계좌 전용. Paper는 자동 통과.
    """
    checks = {}
    sym = signal["symbol"]
    cp = signal["current_price"]
    atr = signal["atr"]

    # 1. 진입 신호
    checks["signal"] = signal["signal"] in ("breakout_long", "breakout_short")

    # 2. ATR 계산
    checks["atr"] = atr > 0

    # 3. 포지션 리스크 ≤ 1%
    if atr > 0:
        shares = int((account_value * TURTLE_RISK_PCT) / atr)
        position_risk_pct = (shares * atr) / account_value
        checks["risk_pct"] = position_risk_pct <= TURTLE_RISK_PCT * 1.05  # 5% 허용 오차
    else:
        shares = 0
        checks["risk_pct"] = False

    # 4. 손절가
    if signal["signal"] == "breakout_long":
        stop_loss = round(cp - TURTLE_STOP_MULT * atr, 2)
    else:
        stop_loss = round(cp + TURTLE_STOP_MULT * atr, 2)
    checks["stop_loss"] = stop_loss > 0

    # 5. 청산 시스템
    checks["exit_system"] = signal.get("system") in ("S1", "S2")

    passed = all(checks.values())
    return {
        "symbol": sym,
        "passed": passed,
        "checks": checks,
        "shares": shares,
        "stop_loss": stop_loss,
        "position_value": round(shares * cp, 2),
        "risk_dollars": round(shares * atr, 2),
        "risk_pct": round((shares * atr) / account_value * 100, 3),
        "system": signal.get("system"),
        "direction": signal.get("direction"),
    }


# ── 진입 로직 ─────────────────────────────────────────────────────────────────

def should_enter(symbol: str, signal: dict, existing_symbols: set, state: dict) -> tuple[bool, str]:
    """진입 여부 결정."""
    if signal["signal"] not in ("breakout_long", "breakout_short"):
        return False, "no_signal"
    if symbol in state.get("turtle_positions", {}):
        return False, "already_tracked"
    if symbol in existing_symbols:
        return False, "already_in_position"
    if len(state["turtle_positions"]) >= MAX_POSITIONS:
        return False, f"max_positions_reached ({MAX_POSITIONS})"
    if signal["atr"] <= 0:
        return False, "atr_zero"
    return True, "ok"


def enter_position(symbol: str, gate: dict, signal: dict, dry_run: bool, state: dict) -> dict:
    """Paper 매수 주문 실행."""
    qty = gate["shares"]
    if qty <= 0:
        return {"status": "skip", "reason": "qty_zero"}

    entry = {
        "ts": now_iso(),
        "action": "enter",
        "symbol": symbol,
        "side": "buy" if gate["direction"] == "long" else "sell",
        "qty": qty,
        "signal": signal["signal"],
        "system": gate["system"],
        "entry_price": signal["current_price"],
        "atr": signal["atr"],
        "stop_loss": gate["stop_loss"],
        "risk_pct": gate["risk_pct"],
        "position_value": gate["position_value"],
        "dry_run": dry_run,
        "gate_passed": gate["passed"],
    }

    if not dry_run and gate["passed"]:
        try:
            order = _alpaca_post("/orders", {
                "symbol": symbol,
                "qty": str(qty),
                "side": entry["side"],
                "type": "market",
                "time_in_force": "day",
            })
            entry["order_id"] = order.get("id", "")[:16]
            entry["status"] = "submitted"
            # 상태 기록
            state["turtle_positions"][symbol] = {
                "entry_ts": entry["ts"],
                "system": gate["system"],
                "entry_price": signal["current_price"],
                "atr": signal["atr"],
                "stop_loss": gate["stop_loss"],
                "qty": qty,
                "side": entry["side"],
            }
        except Exception as e:
            entry["status"] = "error"
            entry["error"] = str(e)
    else:
        entry["status"] = "dry_run" if dry_run else "gate_blocked"

    log_entry(entry)
    return entry


# ── 포지션 관리 ───────────────────────────────────────────────────────────────

def _check_exit_signal(symbol: str, system: str) -> tuple[bool, str]:
    """Turtle 청산 신호 확인."""
    exit_days = 10 if system == "S1" else 20  # S1: 10일 저가, S2: 20일 저가
    bars = _get_bars(symbol, days=exit_days + 5)
    if len(bars) < exit_days + 1:
        return False, "insufficient_bars"

    current_price = float(bars[-1].get("c", 0))
    window = bars[-exit_days - 1:-1]
    exit_low = min(float(b.get("l", 0)) for b in window)

    if current_price < exit_low:
        return True, f"price_below_{exit_days}d_low (${current_price:.2f} < ${exit_low:.2f})"
    return False, "hold"


def manage_positions(positions: list, state: dict, dry_run: bool) -> list[dict]:
    """기존 Turtle 포지션 손절/청산 관리."""
    actions = []
    turtle_syms = set(state["turtle_positions"].keys())

    for pos in positions:
        if "error" in pos:
            continue
        sym = pos["symbol"]
        if sym not in turtle_syms:
            continue  # 수동 포지션은 관리 안 함

        tracked = state["turtle_positions"][sym]
        cp = pos["current_price"]
        stop = pos.get("stop_loss") or tracked.get("stop_loss")
        system = tracked.get("system", "S2")

        reason = None

        # 손절 체크
        if stop and cp < stop:
            reason = f"stop_loss_hit (${cp:.2f} < stop ${stop:.2f})"

        # 청산 신호 체크
        if not reason:
            exit_triggered, exit_msg = _check_exit_signal(sym, system)
            if exit_triggered:
                reason = f"exit_signal: {exit_msg}"

        if reason:
            action = {
                "ts": now_iso(),
                "action": "exit",
                "symbol": sym,
                "side": "sell",
                "qty": int(pos["qty"]),
                "reason": reason,
                "current_price": cp,
                "unrealized_pnl": pos.get("unrealized_pnl"),
                "unrealized_pnl_pct": pos.get("unrealized_pnl_pct"),
                "dry_run": dry_run,
            }
            if not dry_run:
                try:
                    order = _alpaca_post("/orders", {
                        "symbol": sym,
                        "qty": str(int(pos["qty"])),
                        "side": "sell",
                        "type": "market",
                        "time_in_force": "day",
                    })
                    action["order_id"] = order.get("id", "")[:16]
                    action["status"] = "submitted"
                    del state["turtle_positions"][sym]
                except Exception as e:
                    action["status"] = "error"
                    action["error"] = str(e)
            else:
                action["status"] = "dry_run"
            log_entry(action)
            actions.append(action)

    return actions


# ── 메인 ──────────────────────────────────────────────────────────────────────

def run(execute: bool = False) -> dict:
    dry_run = not execute
    state = load_state()
    state.setdefault("turtle_positions", {})

    print(f"{'=' * 60}")
    print(f"Turtle Auto Trader — {'DRY RUN' if dry_run else '*** EXECUTE ***'}")
    print(f"실행시각: {now_iso()}")
    print(f"{'=' * 60}\n")

    # 1. 계좌 조회
    account = get_account_summary()
    if not account.get("ok"):
        print(f"ERROR: 계좌 조회 실패 — {account.get('error')}")
        return {"status": "error", "error": account.get("error")}

    account_value = account["portfolio_value"]
    cash = account["cash"]
    print(f"포트폴리오: ${account_value:,.2f} | 현금: ${cash:,.2f}")
    print(f"Turtle 추적 포지션: {list(state['turtle_positions'].keys()) or '없음'}\n")

    # 2. 기존 포지션 조회
    positions = get_positions()
    existing_syms = {p["symbol"] for p in positions if "error" not in p}
    print(f"현재 Alpaca 포지션: {existing_syms or '없음'}")

    # 3. 기존 Turtle 포지션 관리 (손절/청산)
    print("\n── 포지션 관리 ──")
    exit_actions = manage_positions(positions, state, dry_run)
    if exit_actions:
        for a in exit_actions:
            status = "실행" if not dry_run else "DRY-RUN"
            print(f"  [{status}] EXIT {a['symbol']} — {a['reason']} | P&L: {a.get('unrealized_pnl_pct',0):+.2f}%")
    else:
        print("  청산 대상 없음")

    # 4. 신호 스캔 및 진입
    print("\n── 신호 스캔 ──")
    entered = []
    skipped = []

    for sym in UNIVERSE:
        sym = sym.strip()
        try:
            signal = get_turtle_signal(sym)
        except Exception as e:
            print(f"  {sym}: 신호 조회 실패 — {e}")
            continue

        if signal["signal"] in ("insufficient_data", "error"):
            print(f"  {sym}: 데이터 부족")
            continue

        can_enter, reason = should_enter(sym, signal, existing_syms, state)

        if not can_enter:
            if signal["signal"] != "neutral":
                print(f"  {sym}: 신호 있음({signal['signal']}) but 건너뜀 — {reason}")
            else:
                print(f"  {sym}: 중립 — ${signal['current_price']}")
            skipped.append({"symbol": sym, "reason": reason, "signal": signal["signal"]})
            continue

        # TurtleGate
        gate = turtle_gate_check(signal, account_value)
        gate_status = "PASS" if gate["passed"] else "BLOCK"
        print(f"\n  *** {sym}: {signal['signal']} ({signal['system']}) @ ${signal['current_price']}")
        print(f"      ATR={signal['atr']} | 수량={gate['shares']}주 | 포지션금액=${gate['position_value']:,.2f}")
        print(f"      손절가=${gate['stop_loss']} | 리스크={gate['risk_pct']:.3f}% | TurtleGate={gate_status}")

        if not gate["passed"]:
            print(f"      BLOCKED: {gate['checks']}")
            log_entry({
                "ts": now_iso(), "action": "gate_blocked",
                "symbol": sym, "reason": str(gate["checks"]),
            })
            continue

        result = enter_position(sym, gate, signal, dry_run, state)
        status_msg = "DRY-RUN" if dry_run else f"주문 제출 ({result.get('order_id','')})"
        print(f"      → {status_msg}")
        entered.append(result)

    # 5. 상태 저장
    state["last_run"] = now_iso()
    save_state(state)

    # 6. 요약
    print(f"\n{'=' * 60}")
    print(f"완료 | 진입: {len(entered)}건 | 청산: {len(exit_actions)}건 | 스킵: {len(skipped)}건")
    print(f"Turtle 추적 포지션: {list(state['turtle_positions'].keys()) or '없음'}")
    print(f"{'=' * 60}")

    # 7. Slack 알림
    if entered or exit_actions:
        lines = [f"*Turtle Auto Trader {'DRY-RUN' if dry_run else 'EXECUTED'}* — {now_iso()[:16]}"]
        for a in entered:
            lines.append(f"▶ ENTER {a['symbol']} {a.get('qty')}주 @ ${a.get('entry_price')} [{a.get('system')}] stop=${a.get('stop_loss')}")
        for a in exit_actions:
            lines.append(f"◀ EXIT {a['symbol']} — {a['reason'][:50]} | P&L {a.get('unrealized_pnl_pct',0):+.2f}%")
        post_slack("\n".join(lines))

    return {
        "status": "ok",
        "dry_run": dry_run,
        "entered": len(entered),
        "exited": len(exit_actions),
        "skipped": len(skipped),
        "turtle_positions": list(state["turtle_positions"].keys()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Turtle Auto Trader — Alpaca Paper")
    parser.add_argument("--execute", action="store_true",
                        help="실제 paper 주문 실행 (미지정 시 dry-run)")
    args = parser.parse_args()

    # PAPER_TRADING_AUTO_EXECUTE=true 이거나 --execute 플래그 필요
    execute = args.execute or PAPER_AUTO_EXECUTE
    result = run(execute=execute)
    sys.exit(0 if result.get("status") == "ok" else 1)
