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
# Runtime controls from launchd/container environment must win over .env.
# Otherwise a stale .env can silently bypass entry locks such as MAX_POSITIONS=0.
load_dotenv(ROOT / ".env")

from scripts.alpaca_paper_trading import (
    ALPACA_KEY, ALPACA_SECRET, ALPACA_BASE_URL,
    TURTLE_STOP_MULT, TURTLE_ATR_PERIOD, TURTLE_RISK_PCT,
    get_account_summary, get_positions, get_turtle_signal,
    get_recent_orders, _get_bars, _calc_atr,
)
from scripts.trading_diary import log_trade_entry, log_trade_exit, log_signal_scan
from scripts.harness_turtle_scan import HARNESS_UNIVERSE_META as _UNIVERSE_META
from core.atomic_io import update_json_atomic

_UNIVERSE_INFO: dict[str, dict] = {
    t: {"company_name": cn, "sector": s, "harness_score": sc, "selection_reason": r}
    for t, cn, s, sc, r in _UNIVERSE_META
}

PAPER_AUTO_EXECUTE = os.getenv("PAPER_TRADING_AUTO_EXECUTE", "false").lower() == "true"
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS", "")

LOG_PATH = ROOT / "docs/reports/paper_trading_log.jsonl"
STATE_PATH = ROOT / "docs/reports/paper_trading_positions.json"

# Turtle Trading 진입 유니버스 — **동적 universe.json**(harness_score ≥ 7, US/alpaca) 단일 출처.
# (2026-06-10 통합: 정적 목록 대신 _UNIVERSE_META=동적 메타에서 티커 도출.)
# PAPER_TRADING_UNIVERSE 환경변수가 설정되면 수동 override로 우선한다.
# 청산은 manage_positions가 보유 포지션을 유니버스와 무관하게 검사하므로, 유니버스에서 빠진
# 종목의 기존 포지션도 청산 신호로 정상 정리된다(고아 포지션 없음).
_ENV_UNIVERSE = os.getenv("PAPER_TRADING_UNIVERSE", "").strip()
UNIVERSE = (
    [s.strip() for s in _ENV_UNIVERSE.split(",") if s.strip()]
    if _ENV_UNIVERSE
    else [t for t, _, _, _, _ in _UNIVERSE_META]
)

# #1 무상관 분산 sleeve(2026-06-27 CEO 확정): 측정상관(vs SMH) TLT +0.04·UUP -0.23·GLD +0.18·
# DBC +0.16 = AI 테마와 무상관/역상관. 백테스트 검증: 추가 시 MAR 0.90→1.41(CAGR↑·MaxDD↓).
# 미국상장 ETF라 Alpaca 거래가능. 실거래(IBKR)에선 선물/해외자산으로 더 확장 예정(별도 페이즈).
DIVERSIFIERS = ["TLT", "GLD", "DBC", "UUP"]
PAPER_DIVERSIFY_ENABLED = os.getenv("PAPER_DIVERSIFY_ENABLED", "true").lower() == "true"
if PAPER_DIVERSIFY_ENABLED:
    UNIVERSE = UNIVERSE + [d for d in DIVERSIFIERS if d not in UNIVERSE]

MAX_POSITIONS = int(os.getenv("PAPER_TRADING_MAX_POSITIONS", "6"))

# P0(2026-06-27 red_team_block 후속): 체결 확인 / 상주 손절 운영 파라미터
FILL_TIMEOUT_S = int(os.getenv("PAPER_FILL_TIMEOUT_S", "90"))   # 시장가 주문 체결 대기 상한(초)
FILL_POLL_S = float(os.getenv("PAPER_FILL_POLL_S", "3"))        # 체결 폴링 간격(초)
STOP_TIF = os.getenv("PAPER_STOP_TIF", "gtc")                   # 상주 손절 주문 time_in_force

# P1(F2 상관 한도): 단일 팩터 과집중 차단. 우리 유니버스는 거의 전부 반도체/AI 하드웨어로 상관이
# 높아, 하루 악재에 동시 손절될 위험이 크다(Red Team 2026-06-27 / 진단 F2).
#  ① 동등 ETF(보유종목 대부분 중복)는 동시 보유 금지 — SMH↔SOXX, BOTZ↔ROBO.
#  ② 같은 상관 그룹 동시 보유 유닛 수 상한(기본 3).
EQUIVALENT_ETF_SETS = [frozenset({"SMH", "SOXX"}), frozenset({"BOTZ", "ROBO"})]
# 측정상관 기준 재보정(2026-06-27): ROBO(0.78)·BOTZ(0.78)·QQQ(0.91)는 반도체와 사실상 한 몸 →
# SEMI 그룹으로 통합(기존 ROBOT/별도 분리가 한도를 새게 했던 leak 차단). 무상관 sleeve는 각자 독립 그룹.
CORR_GROUP = {
    # SEMI = AI 하드웨어 복합체(반도체·파운드리·메모리·패키징·포토닉스 — 측정상관 0.7~0.9)
    "SMH": "SEMI", "SOXX": "SEMI", "NVDA": "SEMI", "TSM": "SEMI", "MU": "SEMI",
    "AVGO": "SEMI", "ASX": "SEMI", "QQQ": "SEMI", "ROBO": "SEMI", "BOTZ": "SEMI",
    "COHR": "SEMI",
    "SYM": "ROBOT",
    "TSLA": "AUTO",
    "GOOG": "AIPLATFORM", "META": "AIPLATFORM",   # AI 플랫폼(측정상관 ~0.48)
    "PLTR": "AISW", "SNOW": "AISW", "CRWD": "AISW", "DDOG": "AISW",
    "VRT": "POWER", "CEG": "POWER", "VST": "POWER", "GEV": "POWER", "PWR": "POWER",
    # 무상관/역상관 분산 sleeve — 각자 독립 그룹(상호·반도체와 무상관)
    "TLT": "BOND", "GLD": "GOLD", "DBC": "COMMOD", "UUP": "USD",
}
MAX_UNITS_PER_GROUP = int(os.getenv("PAPER_MAX_CORR_UNITS", "3"))

# 사이징 베이스라인(2026-06-27 CEO 확정): 1N=클래식 Turtle 1유닛(손절 2N에서 실효 리스크 ~2%).
# 백테스트상 2N 사이징(진짜 1%)은 과보수적(CAGR 14.5% vs 1N 22.7%, MAR 0.71 vs 0.93).
# 단일 트레이드 상한 = 2%, 포트폴리오 합산 heat 상한으로 전체 리스크를 통제한다(CLAUDE.md ≤1%→≤2% 개정).
TURTLE_MAX_RISK_PCT = float(os.getenv("PAPER_MAX_TRADE_RISK_PCT", "0.02"))
PAPER_MAX_PORTFOLIO_HEAT = float(os.getenv("PAPER_MAX_PORTFOLIO_HEAT", "0.10"))

# #2 피라미딩(롱 전용, 2026-06-27 백테스트 검증: CAGR 22.7%→32.9%, PF 2.19→2.82).
# 추세가 유리하게 ½N 이동할 때마다 유닛 추가(최대 4), 추가 시 전체 손절을 최근 유닛 -2N 으로 상향.
# 숏은 백테스트상 재앙(MAR 0.16)이라 도입하지 않음.
PAPER_PYRAMID_ENABLED = os.getenv("PAPER_PYRAMID_ENABLED", "true").lower() == "true"
PAPER_MAX_UNITS = int(os.getenv("PAPER_MAX_UNITS", "4"))
PAPER_PYRAMID_STEP_N = float(os.getenv("PAPER_PYRAMID_STEP_N", "0.5"))

# P1(F1 추세필터): 하락·횡보 국면에서 롱 전용 봇이 가짜 돌파를 사 휩쏘로 출혈하는 것을 차단.
# 장기 이동평균(MA) 위에서만 롱 진입을 허용한다(롱·숏 대칭은 short-safe 재설계가 필요한 별도 과제).
TREND_FILTER_ENABLED = os.getenv("PAPER_TREND_FILTER", "true").lower() == "true"
TREND_MA_DAYS = int(os.getenv("PAPER_TREND_MA_DAYS", "100"))

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


# P0 — state 원자화(Red Team 2026-06-27 MAJOR / 메모리 state_file_multiwriter_lock).
# 통째쓰기(save_state) 금지. 모든 변경은 update_json_atomic 으로 *자기 소유 델타*(turtle_positions
# 의 단일 키, last_run)만 적용한다. 이로써 동시 reader/writer 의 lost-update·torn-read 를 차단한다.

def state_set_position(symbol: str, data: dict) -> None:
    def _m(s: dict) -> None:
        s.setdefault("turtle_positions", {})[symbol] = data
    update_json_atomic(STATE_PATH, _m)


def state_pop_position(symbol: str) -> None:
    def _m(s: dict) -> None:
        s.setdefault("turtle_positions", {}).pop(symbol, None)
    update_json_atomic(STATE_PATH, _m)


def state_set_last_run(ts: str) -> None:
    def _m(s: dict) -> None:
        s["last_run"] = ts
    update_json_atomic(STATE_PATH, _m)


def _alpaca_post(path: str, body: dict) -> dict:
    url = f"{ALPACA_BASE_URL}/{path.lstrip('/')}"
    r = requests.post(url, headers={**_HEADERS, "Content-Type": "application/json"},
                      json=body, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Alpaca POST {r.status_code}: {r.text[:300]}")
    return r.json()


def _alpaca_get(path: str) -> dict:
    url = f"{ALPACA_BASE_URL}/{path.lstrip('/')}"
    r = requests.get(url, headers=_HEADERS, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Alpaca GET {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}


def _alpaca_delete(path: str) -> dict:
    url = f"{ALPACA_BASE_URL}/{path.lstrip('/')}"
    r = requests.delete(url, headers=_HEADERS, timeout=15)
    if not r.ok:
        raise RuntimeError(f"Alpaca DELETE {r.status_code}: {r.text[:300]}")
    return r.json() if r.text else {}


def cancel_order(order_id: str) -> None:
    """상주 손절 등 미체결 주문을 취소(이미 체결/소멸이면 무시)."""
    if not order_id:
        return
    try:
        _alpaca_delete(f"/orders/{order_id}")
    except Exception:
        pass


def wait_for_fill(order_id: str, timeout_s: int = FILL_TIMEOUT_S,
                  poll_s: float = FILL_POLL_S) -> tuple[str, float, float]:
    """P0 — 체결 확인 게이트.

    주문이 terminal 상태(filled/canceled/rejected/expired)가 되거나 timeout 까지 폴링한다.
    반환 (status, filled_qty, filled_avg_price). '제출=체결' 가정을 제거해 부분체결·거절·미체결을
    실제 브로커 상태로 확인한 뒤에만 내부 원장/상주손절을 갱신하게 한다(Red Team 2026-06-27 BLOCKER).
    """
    import time
    deadline = time.monotonic() + timeout_s
    last: dict = {}
    terminal = {"filled", "canceled", "cancelled", "rejected", "expired", "done_for_day"}
    timed_out = False
    while True:
        try:
            last = _alpaca_get(f"/orders/{order_id}")
        except Exception as e:
            last = {"status": "unknown", "error": str(e)}
        if str(last.get("status")) in terminal:
            break
        if time.monotonic() >= deadline:
            timed_out = True
            break
        time.sleep(poll_s)
    if timed_out and str(last.get("status")) not in terminal:
        # A timed-out market order can fill later. Cancel it before the caller
        # treats the attempt as not filled, then refresh the final broker state.
        cancel_order(order_id)
        cancel_deadline = time.monotonic() + max(5.0, poll_s * 3)
        while time.monotonic() < cancel_deadline:
            try:
                last = _alpaca_get(f"/orders/{order_id}")
            except Exception as e:
                last = {"status": "cancel_unknown", "error": str(e)}
            if str(last.get("status")) in terminal:
                break
            time.sleep(poll_s)
    fq = float(last.get("filled_qty") or 0)
    fp = float(last.get("filled_avg_price")) if last.get("filled_avg_price") else 0.0
    return str(last.get("status", "unknown")), fq, fp


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
    checks["signal"] = signal["signal"] == "breakout_long"

    # 2. ATR 계산
    checks["atr"] = atr > 0

    # 3. 포지션 리스크 — 1N 사이징(클래식 Turtle 1유닛) + 단일 트레이드 ≤2% 게이트
    #    (2026-06-27 CEO 확정) shares=(계좌×1%)/ATR 로 1N 사이징하되, 손절은 2N 이므로 *실효 손절
    #    리스크는 ~2%*다. gate 는 이 실효 리스크(2N)를 정확히 측정해 ≤2%(TURTLE_MAX_RISK_PCT)로 막는다.
    #    1N 으로 만든 BLOCKER(1N 사이징인데 1N 으로 측정해 ≤1% 통과)는 해소됨 — 측정은 항상 2N 기준.
    #    전체 리스크는 포트폴리오 heat 상한(PAPER_MAX_PORTFOLIO_HEAT)으로 별도 통제.
    if atr > 0:
        shares = int((account_value * TURTLE_RISK_PCT) / atr)
        stop_distance = TURTLE_STOP_MULT * atr
        position_risk_pct = (shares * stop_distance) / account_value  # 실효 손절(2N) 리스크 ~2%
        checks["risk_pct"] = position_risk_pct <= TURTLE_MAX_RISK_PCT * 1.05  # 5% 허용 오차
    else:
        stop_distance = 0
        shares = 0
        checks["risk_pct"] = False

    # 4. 손절가
    stop_loss = round(cp - TURTLE_STOP_MULT * atr, 2)
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
        # 실효 리스크 = 손절까지 거리(2N) × 수량. 1N 이 아니라 실제 손절 손실을 보고한다.
        "risk_dollars": round(shares * stop_distance, 2),
        "risk_pct": round((shares * stop_distance) / account_value * 100, 3) if account_value else 0,
        "system": signal.get("system"),
        "direction": signal.get("direction"),
    }


# ── 진입 로직 ─────────────────────────────────────────────────────────────────

def passes_trend_filter(symbol: str, current_price: float) -> tuple[bool, str]:
    """P1/F1 — 장기 MA 위에서만 롱 허용(하락·횡보 휩쏘 차단). 데이터 부족 시 fail-open(통과+로그)."""
    if not TREND_FILTER_ENABLED:
        return True, "filter_off"
    try:
        bars = _get_bars(symbol, days=TREND_MA_DAYS + 15)
    except Exception as e:
        return True, f"bars_error_failopen({e})"
    closes = [float(b.get("c", 0)) for b in bars if b.get("c")]
    if len(closes) < TREND_MA_DAYS:
        return True, f"insufficient_bars_failopen({len(closes)}<{TREND_MA_DAYS})"
    ma = sum(closes[-TREND_MA_DAYS:]) / TREND_MA_DAYS
    if current_price > ma:
        return True, f"above_ma{TREND_MA_DAYS}(${current_price:.2f}>${ma:.2f})"
    return False, f"below_ma{TREND_MA_DAYS}(${current_price:.2f}<=${ma:.2f})"


def correlation_block(symbol: str, held: set) -> tuple[bool, str]:
    """P1/F2 — 동등 ETF 동시보유 금지 + 상관 그룹 유닛 상한. 막으면 (True, 사유)."""
    su = symbol.upper()
    # ① 동등 ETF 쌍이 이미 보유 중이면 차단(SMH↔SOXX 등 = 사실상 동일 베팅)
    for eq in EQUIVALENT_ETF_SETS:
        if su in eq and (held & (eq - {su})):
            twin = ", ".join(sorted(eq - {su}))
            return True, f"equivalent_etf_held ({twin})"
    # ② 같은 상관 그룹 보유 유닛 수 상한
    grp = CORR_GROUP.get(su)
    if grp:
        same_group = sum(1 for h in held if CORR_GROUP.get(h.upper()) == grp)
        if same_group >= MAX_UNITS_PER_GROUP:
            return True, f"corr_group_full ({grp}={same_group}/{MAX_UNITS_PER_GROUP})"
    return False, ""


def portfolio_heat(state: dict, account_value: float) -> float:
    """현재 보유 포지션의 합산 risk ÷ 계좌. 0~1.
    피라미딩 포지션은 저장된 risk_usd(=총qty×2N)를 우선 사용(엔트리 1개로 계산하면 과소평가)."""
    if not account_value:
        return 0.0
    tot = 0.0
    for p in state.get("turtle_positions", {}).values():
        if p.get("risk_usd") is not None:
            tot += p["risk_usd"]
            continue
        q = p.get("qty", 0) or 0
        e = p.get("entry_price") or 0
        s = p.get("stop_loss") or 0
        if e and s:
            tot += q * abs(e - s)
    return tot / account_value


def should_enter(symbol: str, signal: dict, existing_symbols: set, state: dict) -> tuple[bool, str]:
    """진입 여부 결정."""
    if signal["signal"] != "breakout_long":
        return False, "no_signal"
    if symbol in state.get("turtle_positions", {}):
        return False, "already_tracked"
    if symbol in existing_symbols:
        return False, "already_in_position"
    if len(state["turtle_positions"]) >= MAX_POSITIONS:
        return False, f"max_positions_reached ({MAX_POSITIONS})"
    if signal["atr"] <= 0:
        return False, "atr_zero"
    # P1/F2 — 상관 한도(동등 ETF·그룹 유닛 상한). 현재 보유 = state 추적 ∪ 브로커 실보유.
    held = set(state.get("turtle_positions", {}).keys()) | set(existing_symbols)
    blocked, reason = correlation_block(symbol, held)
    if blocked:
        return False, f"correlation_block: {reason}"
    # P1/F1 — 추세필터(장기 MA 위에서만 롱)
    ok, tnote = passes_trend_filter(symbol, signal["current_price"])
    if not ok:
        return False, f"trend_filter: {tnote}"
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
            order_id = order.get("id", "")
            entry["order_id"] = order_id[:16]

            # P0 — 체결 확인 게이트: '제출'이 아니라 '체결'을 확인한 뒤에만 원장/손절을 갱신.
            status, filled_qty, fill_price = wait_for_fill(order_id)
            entry["order_status"] = status
            entry["filled_qty"] = filled_qty
            if filled_qty <= 0:
                # 미체결/거절 — 내부 원장에 포지션을 만들지 않는다(유령 포지션 방지).
                entry["status"] = "not_filled"
                log_entry(entry)
                return entry

            # 실제 체결가 기준으로 손절가를 확정(고정 stop — 이후 ATR 재계산으로 흔들지 않음).
            fill_price = fill_price or signal["current_price"]
            stop_loss = round(fill_price - TURTLE_STOP_MULT * signal["atr"], 2)
            qty_i = int(filled_qty)

            # P0 — 손절 상주화: 체결 직후 브로커에 stop 매도 주문을 상주시켜, 실행 주기 사이
            # 갭다운/장애에도 장중 손절이 발동되게 한다(Red Team 2026-06-27 BLOCKER).
            stop_order_id = ""
            try:
                so = _alpaca_post("/orders", {
                    "symbol": symbol,
                    "qty": str(qty_i),
                    "side": "sell",
                    "type": "stop",
                    "stop_price": str(stop_loss),
                    "time_in_force": STOP_TIF,
                })
                stop_order_id = so.get("id", "")
            except Exception as se:
                entry["stop_order_error"] = str(se)

            entry["status"] = "filled"
            entry["fill_price"] = fill_price
            entry["stop_loss"] = stop_loss
            entry["stop_order_id"] = stop_order_id[:16]

            # 상태 기록 (원자적 델타 — 자기 키만). 피라미딩 메타 포함(#2).
            rec = {
                "entry_ts": entry["ts"],
                "system": gate["system"],
                "entry_price": fill_price,
                "atr": signal["atr"],
                "stop_loss": stop_loss,
                "qty": qty_i,
                "side": "buy",
                "stop_order_id": stop_order_id,
                "n_at_entry": signal["atr"],          # 첫 유닛 N — ½N 추가 트리거·2N 손절 기준
                "last_unit_price": fill_price,          # 마지막 유닛 진입가
                "unit_count": 1,                        # 보유 유닛 수(피라미딩)
                "risk_usd": round(qty_i * TURTLE_STOP_MULT * signal["atr"], 2),
            }
            state_set_position(symbol, rec)
            # in-memory state 도 동기화(같은 run 내 후속 로직 일관성)
            state.setdefault("turtle_positions", {})[symbol] = dict(rec)
            # 거래 일기 기록 (기업명·섹터·선정 사유 포함) — 실제 체결가/수량 기준
            _info = _UNIVERSE_INFO.get(symbol, {})
            log_trade_entry(
                ticker=symbol,
                side=entry["side"],
                shares=qty_i,
                price=fill_price,
                atr=signal["atr"],
                stop_loss=stop_loss,
                system=gate["system"],
                signal=signal["signal"],
                sector=_info.get("sector", ""),
                harness_score=_info.get("harness_score", 0),
                selection_reason=_info.get("selection_reason", ""),
                note=f"Turtle {gate['system']} 브레이크아웃 자동 진입 | 상주손절 {'OK' if stop_order_id else 'FAIL'}",
            )
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


def reconcile_positions(positions: list, state: dict, dry_run: bool) -> list[dict]:
    """P0 — 브로커 ↔ 내부 원장 정합화(Red Team 2026-06-27 BLOCKER 2건).

    ① 고아 입양: 브로커에 보유 중인 turtle 유니버스 종목이 state 에 없으면 입양해 손절/청산 관리에
       편입한다(없으면 상주 손절도 건다). 수동/비유니버스 포지션은 건드리지 않는다.
    ② 유령 정리: state 에는 있으나 브로커에 없는 종목은 상주 손절이 이미 발동(또는 외부 청산)된
       것으로 보고, 잔여 손절 주문을 취소하고 원장에서 제거(로그)한다.
    """
    actions: list[dict] = []
    universe_set = {s.strip().upper() for s in UNIVERSE}
    broker = {p["symbol"]: p for p in positions if "error" not in p}
    tracked_syms = set(state.get("turtle_positions", {}).keys())

    # ① 고아 입양
    for sym, pos in broker.items():
        if sym in tracked_syms:
            continue
        if sym.upper() not in universe_set:
            continue  # 수동/비유니버스 포지션은 관리 안 함(기존 정책 보존)
        entry = pos.get("entry_price") or pos.get("current_price") or 0
        atr = pos.get("atr") or 0
        if not atr:
            try:
                bars = _get_bars(sym, days=TURTLE_ATR_PERIOD + 5)
                atr = _calc_atr(bars, TURTLE_ATR_PERIOD) if len(bars) >= TURTLE_ATR_PERIOD + 1 else 0
            except Exception:
                atr = 0
        stop = round(entry - TURTLE_STOP_MULT * atr, 2) if atr > 0 else None
        stop_order_id = ""
        if not dry_run and stop and stop > 0:
            try:
                so = _alpaca_post("/orders", {
                    "symbol": sym, "qty": str(int(pos["qty"])), "side": "sell",
                    "type": "stop", "stop_price": str(stop), "time_in_force": STOP_TIF,
                })
                stop_order_id = so.get("id", "")
            except Exception:
                pass
        rec = {
            "entry_ts": now_iso(), "system": "S2",
            "entry_price": entry, "atr": atr, "stop_loss": stop,
            "qty": int(pos["qty"]), "side": "buy", "stop_order_id": stop_order_id,
            "adopted": True,
        }
        if not dry_run:
            state_set_position(sym, rec)
        state.setdefault("turtle_positions", {})[sym] = rec
        act = {"ts": now_iso(), "action": "adopt_orphan", "symbol": sym,
               "stop_loss": stop, "qty": int(pos["qty"]), "dry_run": dry_run,
               "stop_order_id": stop_order_id[:16]}
        log_entry(act)
        actions.append(act)

    # ② 유령 정리
    for sym in list(tracked_syms):
        if sym in broker:
            continue
        tracked = state.get("turtle_positions", {}).get(sym, {})
        if not dry_run:
            cancel_order(tracked.get("stop_order_id", ""))
            try:
                log_trade_exit(
                    ticker=sym, side="sell", shares=int(tracked.get("qty", 0) or 0),
                    price=tracked.get("stop_loss") or tracked.get("entry_price") or 0,
                    entry_price=tracked.get("entry_price", 0),
                    exit_reason="reconcile_stop_filled",
                    note="브로커 미보유 — 상주 손절 발동/외부 청산으로 추정, 원장 정합화",
                )
            except Exception:
                pass
            state_pop_position(sym)
        state.get("turtle_positions", {}).pop(sym, None)
        act = {"ts": now_iso(), "action": "ghost_reconcile", "symbol": sym,
               "dry_run": dry_run, "note": "state had position, broker did not"}
        log_entry(act)
        actions.append(act)

    return actions


def manage_positions(positions: list, state: dict, dry_run: bool) -> list[dict]:
    """기존 Turtle 포지션 손절/청산 관리."""
    actions = []
    # P0 — 먼저 브로커↔원장 정합화(고아 입양/유령 정리)
    actions.extend(reconcile_positions(positions, state, dry_run))

    turtle_syms = set(state.get("turtle_positions", {}).keys())

    for pos in positions:
        if "error" in pos:
            continue
        sym = pos["symbol"]
        if sym not in turtle_syms:
            continue  # 수동 포지션은 관리 안 함

        tracked = state["turtle_positions"][sym]
        cp = pos["current_price"]
        # P0 — 고정 손절 사용: get_positions 가 매번 현재 ATR 로 재계산한 stop 이 아니라, 진입 시
        # 확정한 tracked stop 을 쓴다(Red Team 2026-06-27: ATR 재계산으로 stop 이 흔들리는 문제).
        stop = tracked.get("stop_loss")
        system = tracked.get("system", "S2")

        reason = None

        # 손절 체크 (백업 — 1차 방어선은 브로커 상주 손절. `<=` 로 정확 터치도 포함)
        if stop and cp <= stop:
            reason = f"stop_loss_hit (${cp:.2f} <= stop ${stop:.2f})"

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
                    # 상주 손절 주문을 먼저 취소(중복 매도 방지) 후 시장가 청산.
                    cancel_order(tracked.get("stop_order_id", ""))
                    order = _alpaca_post("/orders", {
                        "symbol": sym,
                        "qty": str(int(pos["qty"])),
                        "side": "sell",
                        "type": "market",
                        "time_in_force": "day",
                    })
                    order_id = order.get("id", "")
                    action["order_id"] = order_id[:16]
                    # 체결 확인 후 실제 체결가로 기록
                    status, filled_qty, fill_price = wait_for_fill(order_id)
                    action["order_status"] = status
                    action["filled_qty"] = filled_qty
                    exit_price = fill_price or cp
                    action["status"] = "filled" if filled_qty > 0 else "not_filled"
                    # 거래 일기 기록 (청산) — 실제 체결가
                    exit_reason_key = "stop_loss" if "stop_loss" in reason else "exit_signal_s2" if "exit_signal" in reason else "manual"
                    log_trade_exit(
                        ticker=sym,
                        side="sell",
                        shares=int(filled_qty or pos["qty"]),
                        price=exit_price,
                        entry_price=tracked.get("entry_price", cp),
                        exit_reason=exit_reason_key,
                        note=reason,
                    )
                    state_pop_position(sym)
                    state.get("turtle_positions", {}).pop(sym, None)
                except Exception as e:
                    action["status"] = "error"
                    action["error"] = str(e)
            else:
                action["status"] = "dry_run"
            log_entry(action)
            actions.append(action)

    return actions


# ── 피라미딩 (#2, 롱 전용) ────────────────────────────────────────────────────

def pyramid_positions(positions: list, state: dict, account_value: float, dry_run: bool) -> list[dict]:
    """추세가 유리하게 ½N 이동할 때마다 유닛 추가(최대 PAPER_MAX_UNITS). 추가 시 전체 손절을
    최근 유닛 -2N 으로 상향하고 상주손절을 교체한다. 롱 전용(숏은 백테스트상 기각)."""
    if not PAPER_PYRAMID_ENABLED:
        return []
    actions: list[dict] = []
    broker = {p["symbol"]: p for p in positions if "error" not in p}
    for sym, tracked in list(state.get("turtle_positions", {}).items()):
        if tracked.get("side") != "buy":
            continue
        if tracked.get("unit_count", 1) >= PAPER_MAX_UNITS:
            continue
        if sym not in broker:
            continue
        N = tracked.get("n_at_entry") or tracked.get("atr") or 0
        if N <= 0:
            continue
        cur = broker[sym].get("current_price") or 0
        last = tracked.get("last_unit_price") or tracked.get("entry_price") or 0
        trigger = last + PAPER_PYRAMID_STEP_N * N
        if not cur or cur < trigger:
            continue

        qty_add = int((account_value * TURTLE_RISK_PCT) / N)
        if qty_add <= 0:
            continue
        old_qty = int(tracked.get("qty", 0) or 0)
        new_total = old_qty + qty_add
        new_stop = round(cur - TURTLE_STOP_MULT * N, 2)
        new_risk = round(new_total * TURTLE_STOP_MULT * N, 2)

        # heat 상한: 이 포지션 risk 를 신규치로 교체했을 때 합산 heat 가 상한 이하인가
        old_risk = tracked.get("risk_usd") or 0
        prospective_heat = portfolio_heat(state, account_value) + (new_risk - old_risk) / account_value if account_value else 1
        if prospective_heat > PAPER_MAX_PORTFOLIO_HEAT:
            actions.append({"ts": now_iso(), "action": "pyramid_skip", "symbol": sym,
                            "reason": "heat_cap", "unit_to": tracked.get("unit_count", 1) + 1})
            log_entry(actions[-1])
            continue

        action = {"ts": now_iso(), "action": "pyramid_add", "symbol": sym,
                  "unit": tracked.get("unit_count", 1) + 1, "qty_add": qty_add,
                  "price": cur, "new_total_qty": new_total, "new_stop": new_stop,
                  "dry_run": dry_run}

        if not dry_run:
            try:
                order = _alpaca_post("/orders", {
                    "symbol": sym, "qty": str(qty_add), "side": "buy",
                    "type": "market", "time_in_force": "day",
                })
                status, filled_qty, fill_price = wait_for_fill(order.get("id", ""))
                action["order_status"] = status
                if filled_qty <= 0:
                    action["status"] = "not_filled"
                    log_entry(action)
                    actions.append(action)
                    continue
                fill_price = fill_price or cur
                new_total = old_qty + int(filled_qty)
                new_stop = round(fill_price - TURTLE_STOP_MULT * N, 2)
                new_risk = round(new_total * TURTLE_STOP_MULT * N, 2)
                # 상주손절 교체: 기존 취소 → 전체 수량으로 재배치
                cancel_order(tracked.get("stop_order_id", ""))
                new_stop_id = ""
                try:
                    so = _alpaca_post("/orders", {
                        "symbol": sym, "qty": str(new_total), "side": "sell",
                        "type": "stop", "stop_price": str(new_stop), "time_in_force": STOP_TIF,
                    })
                    new_stop_id = so.get("id", "")
                except Exception as se:
                    action["stop_order_error"] = str(se)
                updated = dict(tracked)
                updated.update({
                    "qty": new_total, "stop_loss": new_stop,
                    "last_unit_price": fill_price,
                    "unit_count": tracked.get("unit_count", 1) + 1,
                    "stop_order_id": new_stop_id, "risk_usd": new_risk,
                })
                state_set_position(sym, updated)
                state["turtle_positions"][sym] = dict(updated)
                action.update({"status": "filled", "fill_price": fill_price,
                               "new_total_qty": new_total, "new_stop": new_stop,
                               "stop_order_id": new_stop_id[:16]})
                log_trade_entry(
                    ticker=sym, side="buy", shares=int(filled_qty), price=fill_price,
                    atr=N, stop_loss=new_stop, system=tracked.get("system", "S2"),
                    signal="pyramid_add",
                    sector="", harness_score=0, selection_reason="",
                    note=f"피라미딩 유닛 {action['unit']}/{PAPER_MAX_UNITS} | 손절상향 ${new_stop}",
                )
            except Exception as e:
                action["status"] = "error"
                action["error"] = str(e)
        else:
            action["status"] = "dry_run"
            # in-memory 반영(같은 run 일관성)
            sim = dict(tracked)
            sim.update({"qty": new_total, "stop_loss": new_stop, "last_unit_price": cur,
                        "unit_count": tracked.get("unit_count", 1) + 1, "risk_usd": new_risk})
            state["turtle_positions"][sym] = sim

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
    mgmt_actions = manage_positions(positions, state, dry_run)
    status = "실행" if not dry_run else "DRY-RUN"
    exit_actions = [a for a in mgmt_actions if a.get("action") == "exit"]
    reconcile_acts = [a for a in mgmt_actions if a.get("action") in ("adopt_orphan", "ghost_reconcile")]
    for a in reconcile_acts:
        if a["action"] == "adopt_orphan":
            print(f"  [{status}] ADOPT {a['symbol']} — 고아 입양 stop=${a.get('stop_loss')}")
        else:
            print(f"  [{status}] RECONCILE {a['symbol']} — 유령 정리(브로커 미보유)")
    if exit_actions:
        for a in exit_actions:
            print(f"  [{status}] EXIT {a['symbol']} — {a['reason']} | P&L: {a.get('unrealized_pnl_pct',0) or 0:+.2f}%")
    elif not reconcile_acts:
        print("  청산 대상 없음")

    # 3b. 피라미딩 (#2, 롱 전용) — 추세 유리 시 유닛 추가
    print("\n── 피라미딩 ──")
    pyramid_actions = pyramid_positions(positions, state, account_value, dry_run)
    adds = [a for a in pyramid_actions if a.get("action") == "pyramid_add"]
    if adds:
        for a in adds:
            print(f"  [{status}] PYRAMID {a['symbol']} 유닛{a['unit']}/{PAPER_MAX_UNITS} +{a['qty_add']}주 @${a['price']} → 총{a['new_total_qty']}주 stop=${a['new_stop']}")
    else:
        print("  추가 대상 없음")

    # 4. 신호 스캔 및 진입
    print("\n── 신호 스캔 ──")
    entered = []
    skipped = []

    # Finding 3(Red Team 2026-06-10): MAX_POSITIONS 선착순 슬롯 선점 방지.
    # harness_score 내림차순으로 진입 순서를 정렬해 동시 돌파 시 고확신 종목이 한정 슬롯을
    # 먼저 차지하게 한다. (Turtle 원칙 준수: 기존 포지션을 점수로 교체하지 않음 — 순서만 조정)
    entry_order = sorted(
        (s.strip() for s in UNIVERSE),
        key=lambda s: _UNIVERSE_INFO.get(s, {}).get("harness_score", 0),
        reverse=True,
    )
    for sym in entry_order:
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

        # 포트폴리오 heat 상한: 기존 보유 risk 합 + 신규 risk ≤ HEAT_CAP × 계좌
        cur_heat = portfolio_heat(state, account_value)
        new_heat = (gate["risk_dollars"] / account_value) if account_value else 0
        if cur_heat + new_heat > PAPER_MAX_PORTFOLIO_HEAT:
            print(f"      heat 상한 초과 — 건너뜀 (보유 {cur_heat*100:.1f}% + 신규 {new_heat*100:.1f}% > {PAPER_MAX_PORTFOLIO_HEAT*100:.0f}%)")
            log_entry({"ts": now_iso(), "action": "heat_blocked", "symbol": sym,
                       "cur_heat": round(cur_heat, 4), "new_heat": round(new_heat, 4),
                       "cap": PAPER_MAX_PORTFOLIO_HEAT})
            skipped.append({"symbol": sym, "reason": "heat_cap", "signal": signal["signal"]})
            continue

        result = enter_position(sym, gate, signal, dry_run, state)
        status_msg = "DRY-RUN" if dry_run else f"주문 제출 ({result.get('order_id','')})"
        print(f"      → {status_msg}")
        entered.append(result)

    # 5. 상태 저장 + 신호 스캔 일기 기록
    # P0 — 통째쓰기 금지. enter/manage 가 이미 각자 델타를 원자적으로 저장했으므로
    # 여기서는 last_run 만 원자적으로 갱신한다(다른 writer 필드 보존).
    state["last_run"] = now_iso()
    state_set_last_run(state["last_run"])
    try:
        all_signals = []
        for sym in UNIVERSE:
            try:
                sig = get_turtle_signal(sym.strip())
                sig["ticker"] = sym.strip()
                all_signals.append(sig)
            except Exception:
                pass
        log_signal_scan(all_signals, account_value)
    except Exception:
        pass

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
