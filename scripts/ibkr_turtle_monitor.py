"""
IBKR Turtle Trading Monitor — 포지션 모니터링 + 신호 스캔
ib_insync 기반. TWS / IB Gateway가 실행 중이어야 함 (포트 4002, 페이퍼 트레이딩).

현재 운용 계좌
  계좌 ID  : DUQ416334
  계좌 유형 : Simulated Trading (IBKR Paper Trading)
  접속 방식 : IB Gateway → 127.0.0.1:4002
  로그인    : vvgfmt298 (Paper Trading 계정)

실행 모드:
  python scripts/ibkr_turtle_monitor.py           # 터미널 pretty-print (dry-run)
  python scripts/ibkr_turtle_monitor.py --execute # EXIT 신호 포지션에 GTC 매도 주문
  python scripts/ibkr_turtle_monitor.py --json    # 구조화된 JSON 한 줄 출력 (stdout)

전제조건:
  1. IB Gateway 실행 중 (~/Applications/IB Gateway 10.45/)
  2. 포트 4002 API 활성화, Read-Only API 해제
  3. .venv에 ib_insync 설치됨
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

# ── 설정 ──────────────────────────────────────────────────────────────────────

TWS_HOST = "127.0.0.1"

# IBKR_TRADING_MODE=paper (기본) → IB Gateway 페이퍼 포트 4002
# IBKR_TRADING_MODE=live         → IB Gateway 실전 포트 4001
IBKR_TRADING_MODE = os.getenv("IBKR_TRADING_MODE", "paper").strip().lower()
TWS_PORT = 4002 if IBKR_TRADING_MODE == "paper" else 4001
TWS_CLIENT_ID = 11       # paper_trader(10)와 충돌 방지

LOG_PATH   = ROOT / "docs" / "reports" / "ibkr_turtle_monitor.jsonl"
STATE_PATH = ROOT / "docs" / "reports" / "ibkr_tws_positions.json"
UNIVERSE_PATH = ROOT / "docs" / "trading" / "universe.json"

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Harness 리서치 유니버스 (fallback: universe.json 없을 때 사용)
UNIVERSE_FALLBACK: list[dict] = [
    # Physical AI / AGI 인프라 (미국)
    {"region": "US", "symbol": "NVDA", "exchange": "SMART", "currency": "USD", "name": "NVIDIA",             "sector": "AI Chip"},
    {"region": "US", "symbol": "AVGO", "exchange": "SMART", "currency": "USD", "name": "Broadcom",           "sector": "AI Chip"},
    {"region": "US", "symbol": "TSM",  "exchange": "NYSE",  "currency": "USD", "name": "TSMC ADR",           "sector": "Foundry"},
    {"region": "US", "symbol": "MU",   "exchange": "SMART", "currency": "USD", "name": "Micron Technology",  "sector": "Memory"},
    {"region": "US", "symbol": "ANET", "exchange": "SMART", "currency": "USD", "name": "Arista Networks",    "sector": "AI Network"},
    {"region": "US", "symbol": "VRT",  "exchange": "NYSE",  "currency": "USD", "name": "Vertiv",             "sector": "Power Infra"},
    {"region": "US", "symbol": "TER",  "exchange": "SMART", "currency": "USD", "name": "Teradyne",           "sector": "Test Equip"},
    {"region": "US", "symbol": "SYM",  "exchange": "SMART", "currency": "USD", "name": "Symbotic",           "sector": "Robotics"},
    {"region": "US", "symbol": "ISRG", "exchange": "SMART", "currency": "USD", "name": "Intuitive Surgical", "sector": "Medical Robot"},
    {"region": "US", "symbol": "ROK",  "exchange": "NYSE",  "currency": "USD", "name": "Rockwell Automation","sector": "Industrial Auto"},
    # 전력 인프라
    {"region": "US", "symbol": "CEG",  "exchange": "SMART", "currency": "USD", "name": "Constellation Energy","sector": "Power"},
    {"region": "US", "symbol": "VST",  "exchange": "NYSE",  "currency": "USD", "name": "Vistra",             "sector": "Power"},
    {"region": "US", "symbol": "GEV",  "exchange": "NYSE",  "currency": "USD", "name": "GE Vernova",         "sector": "Power Equip"},
    {"region": "US", "symbol": "PWR",  "exchange": "NYSE",  "currency": "USD", "name": "Quanta Services",    "sector": "Power Infra"},
]

# Turtle 파라미터
TURTLE_S1_ENTRY  = 20   # S1 진입: 20일 고가 돌파
TURTLE_S2_ENTRY  = 55   # S2 진입: 55일 고가 돌파
TURTLE_S1_EXIT   = 10   # S1 청산: 10일 저가 하회
TURTLE_S2_EXIT   = 20   # S2 청산: 20일 저가 하회 (주요 청산선)
TURTLE_ATR_DAYS  = 20   # ATR 계산 기간
TURTLE_STOP_MULT = 2.0  # 손절 = 진입가 - 2×ATR
TURTLE_RISK_PCT  = 0.01 # 계좌 리스크 1%

# ── 외환 환율 (포지션 사이징 USD 환산용) ──────────────────────────────────────

# 기본 환율 (USD 기준 1 로컬 통화 = ? USD) — 근사값
_FOREX_FALLBACK: dict[str, float] = {
    "KRW": 1 / 1380,   # 1 KRW ≈ 0.000725 USD
    "JPY": 1 / 155,    # 1 JPY ≈ 0.00645 USD
    "TWD": 1 / 32,     # 1 TWD ≈ 0.03125 USD
    "HKD": 1 / 7.8,    # 1 HKD ≈ 0.1282 USD
    "USD": 1.0,
}
_forex_cache: dict[str, float] = {}


def get_usd_rate(ib: "object | None", currency: str) -> float:
    """로컬 통화 1단위 = ? USD 반환. IBKR 조회 실패 시 근사값 fallback. 절대 예외 없음."""
    if currency == "USD":
        return 1.0
    if currency in _forex_cache:
        return _forex_cache[currency]
    rate = _FOREX_FALLBACK.get(currency, 1.0)
    if ib is not None:
        try:
            from ib_insync import Forex
            pair = Forex(f"USD{currency}")
            ib.qualifyContracts(pair)
            bars = ib.reqHistoricalData(
                pair, endDateTime="", durationStr="2 D",
                barSizeSetting="1 day", whatToShow="MIDPOINT",
                useRTH=True, formatDate=1,
            )
            if bars:
                usd_per_local = 1.0 / bars[-1].close  # bars[-1].close = 1 USD당 로컬 통화 수
                _forex_cache[currency] = usd_per_local
                return usd_per_local
        except Exception:
            pass
    _forex_cache[currency] = rate
    return rate


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _p(msg: str, json_mode: bool) -> None:
    """json_mode일 때는 stderr로, 아닐 때는 stdout으로 출력."""
    if json_mode:
        print(msg, file=sys.stderr)
    else:
        print(msg)


def load_universe() -> tuple[list[dict], str]:
    """universe.json이 있으면 동적 로드, 없으면 fallback."""
    if UNIVERSE_PATH.exists():
        try:
            data = json.loads(UNIVERSE_PATH.read_text())
            if isinstance(data, list) and len(data) > 0:
                return data, "universe.json"
        except Exception:
            pass
    return UNIVERSE_FALLBACK, "hardcoded"


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"positions": {}, "last_run": None}


def save_state(s: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(s, indent=2, ensure_ascii=False))


def log_entry(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def send_slack(msg: str) -> None:
    if not SLACK_WEBHOOK_URL:
        return
    try:
        import urllib.request
        body = json.dumps({"text": msg}).encode()
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL, data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


# ── 가격 히스토리 + Turtle 계산 ───────────────────────────────────────────────

def calc_full_signal(ib, contract, json_mode: bool) -> dict | None:
    """S1/S2 진입 신호 + S1/S2 청산 저가 + ATR 계산."""
    try:
        from ib_insync import IB  # noqa: F401
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="90 D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )
        if not bars or len(bars) < TURTLE_S2_ENTRY + 2:
            _p(f"  [{contract.symbol}] 데이터 부족 (bar 수: {len(bars) if bars else 0})", json_mode)
            return None

        closes = [b.close for b in bars]
        highs  = [b.high  for b in bars]
        lows   = [b.low   for b in bars]

        current_price = closes[-1]

        # 진입 신호
        s1_high = max(highs[-TURTLE_S1_ENTRY - 1:-1])
        s2_high = max(highs[-TURTLE_S2_ENTRY - 1:-1])
        s1_entry = current_price > s1_high
        s2_entry = current_price > s2_high

        if s2_entry:
            signal = "breakout_long"
            active_signal = "S2"
        elif s1_entry:
            signal = "breakout_long"
            active_signal = "S1"
        else:
            signal = "neutral"
            active_signal = None

        # 청산 기준 (10일 저가, 20일 저가)
        s1_low = min(lows[-TURTLE_S1_EXIT - 1:-1])
        s2_low = min(lows[-TURTLE_S2_EXIT - 1:-1])

        # 20일 ATR
        tr_list = []
        for i in range(-TURTLE_ATR_DAYS, 0):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i]  - closes[i - 1]),
            )
            tr_list.append(tr)
        atr = sum(tr_list) / len(tr_list)

        gap_s2_pct = (current_price - s2_high) / s2_high * 100 if s2_high > 0 else None

        return {
            "symbol":        contract.symbol,
            "current_price": round(current_price, 2),
            "s1_high":       round(s1_high, 2),
            "s2_high":       round(s2_high, 2),
            "s1_low":        round(s1_low, 2),
            "s2_low":        round(s2_low, 2),
            "atr":           round(atr, 4),
            "signal":        signal,
            "active_signal": active_signal,
            "gap_pct":       round(gap_s2_pct, 2) if gap_s2_pct is not None else None,
        }
    except Exception as e:
        _p(f"  [{contract.symbol}] 신호 계산 실패: {e}", json_mode)
        return None



def assess_position(pos_meta: dict, sig: dict | None) -> dict:
    """포지션 + 신호 데이터를 결합해 action과 위험 지표 계산."""
    entry_price = pos_meta.get("entry_price", 0)
    atr         = pos_meta.get("atr", 0)
    stop_loss   = pos_meta.get("stop_loss", entry_price - TURTLE_STOP_MULT * atr)
    qty         = pos_meta.get("qty", 0)
    exchange    = pos_meta.get("exchange", "SMART")
    entry_ts    = pos_meta.get("entry_ts", "")

    current_price    = sig["current_price"] if sig else None
    market_value     = round(current_price * qty, 2) if current_price is not None else None
    unrealized_pnl   = round((current_price - entry_price) * qty, 2) if current_price is not None else None
    unrealized_pnl_pct = (
        round((current_price - entry_price) / entry_price * 100, 3)
        if current_price is not None and entry_price > 0 else None
    )

    s1_low = sig["s1_low"] if sig else None
    s2_low = sig["s2_low"] if sig else None

    stop_distance_pct = (
        round((current_price - stop_loss) / current_price * 100, 2)
        if current_price is not None and current_price > 0 else None
    )
    s1_distance_pct = (
        round((current_price - s1_low) / current_price * 100, 2)
        if current_price is not None and s1_low is not None and current_price > 0 else None
    )
    s2_distance_pct = (
        round((current_price - s2_low) / current_price * 100, 2)
        if current_price is not None and s2_low is not None and current_price > 0 else None
    )

    # 액션 결정
    action = "HOLD"
    if current_price is not None:
        if current_price <= stop_loss:
            action = "STOP_LOSS"
        elif s1_low is not None and current_price <= s1_low:
            action = "S1_EXIT"
        elif s2_low is not None and current_price <= s2_low:
            action = "S2_EXIT"

    near_stop = stop_distance_pct is not None and stop_distance_pct < 10.0
    near_s1   = s1_distance_pct is not None and s1_distance_pct < 5.0

    return {
        "symbol":             pos_meta.get("symbol", ""),
        "exchange":           exchange,
        "qty":                qty,
        "entry_ts":           entry_ts,
        "entry_price":        entry_price,
        "current_price":      current_price,
        "market_value":       market_value,
        "unrealized_pnl":     unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "atr":                atr,
        "stop_loss":          round(stop_loss, 2),
        "stop_distance_pct":  stop_distance_pct,
        "s1_low":             s1_low,
        "s1_distance_pct":    s1_distance_pct,
        "s2_low":             s2_low,
        "s2_distance_pct":    s2_distance_pct,
        "action":             action,
        "near_stop":          near_stop,
        "near_s1":            near_s1,
    }


# ── 메인 실행 ─────────────────────────────────────────────────────────────────

def run(execute: bool = False, json_mode: bool = False) -> dict:
    """
    모니터 실행.
    json_mode=True: 결과 dict 반환 (stdout에 JSON 출력은 caller가 담당)
    """
    ts = now_iso()
    universe, universe_source = load_universe()
    state = load_state()
    state.setdefault("positions", {})

    _p("=" * 62, json_mode)
    _p(f"IBKR Turtle Monitor — {'EXECUTE' if execute else 'DRY RUN'} | {ts}", json_mode)
    _p(f"Universe: {len(universe)} 종목 ({universe_source})", json_mode)
    _p("=" * 62, json_mode)

    # ── IB 연결 시도 ─────────────────────────────────────────────────────────
    gateway_connected = False
    account_data: dict | None = None
    ib = None

    try:
        from ib_insync import IB, Stock, LimitOrder, util
        util.logToConsole(False)

        ib = IB()
        ib.connect(TWS_HOST, TWS_PORT, clientId=TWS_CLIENT_ID, timeout=10)
        gateway_connected = True
        _p(f"게이트웨이 연결 성공 (포트 {TWS_PORT}, clientId={TWS_CLIENT_ID})", json_mode)

        # 계좌 정보
        accounts = ib.managedAccounts()
        paper_account = next(
            (a for a in accounts if a.startswith("DU")), accounts[0] if accounts else ""
        )
        _p(f"계좌: {paper_account}", json_mode)

        nav_vals = ib.accountValues(account=paper_account)
        nav  = next((float(v.value) for v in nav_vals if v.tag == "NetLiquidation" and v.currency == "USD"), 0)
        cash = next((float(v.value) for v in nav_vals if v.tag == "TotalCashValue" and v.currency == "USD"), 0)

        baseline_nav = state.get("baseline", {}).get("nav", nav)
        total_pnl = round(nav - baseline_nav, 2)
        total_pnl_pct = round(total_pnl / baseline_nav * 100, 3) if baseline_nav > 0 else 0.0

        account_data = {
            "account_id":   paper_account,
            "nav":          round(nav, 2),
            "cash":         round(cash, 2),
            "baseline_nav": round(baseline_nav, 2),
            "total_pnl":    total_pnl,
            "total_pnl_pct": total_pnl_pct,
        }
        _p(f"NAV: ${nav:,.2f} | 현금: ${cash:,.2f} | 총 손익: ${total_pnl:+,.2f} ({total_pnl_pct:+.3f}%)", json_mode)

    except Exception as e:
        _p(f"[경고] 게이트웨이 연결 실패: {e}", json_mode)
        _p("  → 상태 파일에서 포지션 정보만 읽습니다.", json_mode)
        if state.get("baseline"):
            baseline_nav = state["baseline"].get("nav", 0)
        else:
            baseline_nav = 0
        account_data = None

    # ── 포지션 평가 ──────────────────────────────────────────────────────────
    _p("\n── 포지션 평가 ──", json_mode)
    position_results: list[dict] = []
    exit_signals: list[str] = []
    exit_contracts: list[tuple] = []  # (symbol, qty) for execute mode

    held_symbols = set(state["positions"].keys())

    for sym, meta in state["positions"].items():
        meta["symbol"] = sym
        sig = None

        if gateway_connected and ib is not None:
            try:
                from ib_insync import Stock
                u_item = next((u for u in universe if u["symbol"] == sym), None)
                exchange = u_item["exchange"] if u_item else meta.get("exchange", "SMART")
                currency = u_item.get("currency", "USD") if u_item else "USD"
                contract = Stock(sym, exchange, currency)
                ib.qualifyContracts(contract)
                sig = calc_full_signal(ib, contract, json_mode)
            except Exception as e:
                _p(f"  [{sym}] 신호 계산 중 오류: {e}", json_mode)

        assessed = assess_position(meta, sig)
        position_results.append(assessed)

        action = assessed["action"]
        cp = assessed["current_price"]
        pnl_pct = assessed["unrealized_pnl_pct"]
        pnl_str = f"{pnl_pct:+.3f}%" if pnl_pct is not None else "—"
        cp_str  = f"${cp:.2f}" if cp is not None else "연결 안됨"

        if action == "HOLD":
            _p(f"  {sym}: HOLD {cp_str} | 손익 {pnl_str} | 손절 ${assessed['stop_loss']:.2f} ({assessed['stop_distance_pct'] or '—'}% 여유)", json_mode)
        else:
            _p(f"  {sym}: *** {action} *** {cp_str} | 손익 {pnl_str}", json_mode)
            exit_signals.append(sym)
            exit_contracts.append((sym, meta.get("qty", 0), meta.get("exchange", "SMART")))

    if not position_results:
        _p("  현재 보유 포지션 없음", json_mode)

    # ── EXIT 실행 ────────────────────────────────────────────────────────────
    if execute and exit_signals and gateway_connected and ib is not None:
        _p(f"\n── EXIT 실행 ({len(exit_signals)}건) ──", json_mode)
        exited = []
        for sym, qty, exchange in exit_contracts:
            try:
                from ib_insync import Stock, MarketOrder
                u_item = next((u for u in universe if u["symbol"] == sym), None)
                currency = u_item.get("currency", "USD") if u_item else "USD"
                contract = Stock(sym, exchange, currency)
                ib.qualifyContracts(contract)
                order = MarketOrder("SELL", qty)
                order.tif = "GTC"
                trade = ib.placeOrder(contract, order)
                ib.sleep(2)
                _p(f"  {sym}: 매도 주문 제출 (orderId={trade.order.orderId}, qty={qty})", json_mode)
                log_entry({
                    "ts": now_iso(), "action": "exit", "symbol": sym,
                    "qty": qty, "exchange": exchange, "trigger": "monitor_exit",
                    "dry_run": False,
                })
                exited.append(sym)
                # 상태에서 제거
                state["positions"].pop(sym, None)
            except Exception as e:
                _p(f"  {sym}: 매도 주문 실패: {e}", json_mode)

        if exited:
            state["last_run"] = now_iso()
            save_state(state)
            slack_msg = (
                f"[IBKR Turtle Monitor] EXIT 실행\n"
                f"종목: {', '.join(exited)}\n"
                f"시각: {now_iso()}"
            )
            send_slack(slack_msg)
            _p(f"  → {len(exited)}건 청산 완료. 상태 파일 업데이트.", json_mode)

    elif exit_signals:
        _p(f"\n[⚠] EXIT 신호 감지: {', '.join(exit_signals)} — --execute 없이 실행 중, 주문 미발행", json_mode)

    # ── 진입 신호 스캔 ────────────────────────────────────────────────────────
    _p("\n── 진입 신호 스캔 ──", json_mode)
    entry_candidates: list[dict] = []

    if gateway_connected and ib is not None:
        for u_item in universe:
            sym      = u_item["symbol"]
            exchange = u_item.get("exchange", "SMART")
            currency = u_item.get("currency", "USD")
            region   = u_item.get("region", "US")
            name     = u_item.get("name", "")
            sector   = u_item.get("sector", "")
            in_pos   = sym in held_symbols

            try:
                from ib_insync import Stock
                contract = Stock(sym, exchange, currency)
                ib.qualifyContracts(contract)
                sig = calc_full_signal(ib, contract, json_mode)
            except Exception as e:
                _p(f"  [{sym}] 스캔 오류: {e}", json_mode)
                sig = None

            if sig:
                cand = {
                    "symbol":        sym,
                    "region":        region,
                    "name":          name,
                    "sector":        sector,
                    "currency":      currency,
                    "current_price": sig["current_price"],
                    "s1_high":       sig["s1_high"],
                    "s2_high":       sig["s2_high"],
                    "atr":           sig["atr"],
                    "signal":        sig["signal"],
                    "active_signal": sig["active_signal"],
                    "gap_pct":       sig["gap_pct"],
                    "in_position":   in_pos,
                }
                entry_candidates.append(cand)

                sig_str = f"*** {sig['signal'].upper()} ({sig['active_signal']}) ***" if sig["signal"] != "neutral" else "중립"
                _p(f"  [{region}] {sym}: {sig['current_price']:.4g} {currency} | S1고점 {sig['s1_high']:.4g} | S2고점 {sig['s2_high']:.4g} | {sig_str}", json_mode)
            else:
                entry_candidates.append({
                    "symbol":        sym,
                    "region":        region,
                    "name":          name,
                    "sector":        sector,
                    "currency":      currency,
                    "current_price": None,
                    "s1_high":       None,
                    "s2_high":       None,
                    "atr":           None,
                    "signal":        "insufficient_data",
                    "active_signal": None,
                    "gap_pct":       None,
                    "in_position":   in_pos,
                })
    else:
        # 게이트웨이 없을 때: 상태에 있는 종목만 in_position 표시
        _p("  게이트웨이 미연결 — 진입 신호 스캔 불가", json_mode)
        for u_item in universe:
            sym = u_item["symbol"]
            entry_candidates.append({
                "symbol":        sym,
                "region":        u_item.get("region", "US"),
                "name":          u_item.get("name", ""),
                "sector":        u_item.get("sector", ""),
                "currency":      u_item.get("currency", "USD"),
                "current_price": None,
                "s1_high":       None,
                "s2_high":       None,
                "atr":           None,
                "signal":        "no_connection",
                "active_signal": None,
                "gap_pct":       None,
                "in_position":   sym in held_symbols,
            })

    # ── IB 연결 해제 ─────────────────────────────────────────────────────────
    if ib is not None and gateway_connected:
        try:
            ib.disconnect()
        except Exception:
            pass

    state["last_run"] = now_iso()

    # NAV 이력 축적 (포트폴리오 차트용)
    if account_data:
        history = state.setdefault("nav_history", [])
        today = ts[:10]  # YYYY-MM-DD
        baseline = account_data["baseline_nav"]
        pnl_pct = account_data["total_pnl_pct"]
        # 같은 날 기록이 있으면 최신값으로 갱신, 없으면 추가
        existing = next((i for i, h in enumerate(history) if h.get("date") == today), None)
        snap = {"date": today, "value": account_data["nav"], "pnl_pct": pnl_pct}
        if existing is not None:
            history[existing] = snap
        else:
            history.append(snap)
        # 최대 90일치 유지
        state["nav_history"] = history[-90:]

    save_state(state)

    # 프론트엔드 차트용 이력 (날짜 레이블 MM/DD로 변환)
    raw_history = state.get("nav_history", [])
    chart_history = []
    for h in raw_history:
        try:
            from datetime import datetime as _dt
            d = _dt.strptime(h["date"], "%Y-%m-%d")
            chart_history.append({
                "date": d.strftime("%m/%d"),
                "value": h["value"],
                "pnl_pct": h.get("pnl_pct", 0.0),
            })
        except Exception:
            pass

    _p(f"\n완료 | 포지션: {len(position_results)}건 | EXIT 신호: {len(exit_signals)}건 | 스캔: {len(entry_candidates)}종목", json_mode)

    return {
        "ok":               True,
        "ts":               ts,
        "mode":             IBKR_TRADING_MODE,
        "gateway_connected": gateway_connected,
        "account":          account_data,
        "positions":        position_results,
        "exit_signals":     exit_signals,
        "entry_candidates": entry_candidates,
        "universe_source":  universe_source,
        "nav_history":      chart_history,
        "error":            None,
    }


def run_offline() -> dict:
    """게이트웨이 없이 상태 파일만 읽어 최소 결과를 반환 (fallback)."""
    state = load_state()
    universe, universe_source = load_universe()
    positions = []
    for sym, meta in state.get("positions", {}).items():
        meta["symbol"] = sym
        assessed = assess_position(meta, None)
        positions.append(assessed)
    candidates = [
        {
            "symbol":        u["symbol"],
            "region":        u.get("region", "US"),
            "name":          u.get("name", ""),
            "sector":        u.get("sector", ""),
            "currency":      u.get("currency", "USD"),
            "current_price": None,
            "s1_high":       None,
            "s2_high":       None,
            "atr":           None,
            "signal":        "no_connection",
            "active_signal": None,
            "gap_pct":       None,
            "in_position":   u["symbol"] in state.get("positions", {}),
        }
        for u in universe
    ]
    return {
        "ok":               True,
        "ts":               now_iso(),
        "mode":             IBKR_TRADING_MODE,
        "gateway_connected": False,
        "account":          None,
        "positions":        positions,
        "exit_signals":     [],
        "entry_candidates": candidates,
        "universe_source":  universe_source,
        "error":            "Gateway offline — state file only",
    }


# ── 진입점 ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBKR Turtle Trading Monitor")
    parser.add_argument("--execute", action="store_true", help="EXIT 신호 시 GTC 매도 주문 발행")
    parser.add_argument("--json",    action="store_true", help="JSON 단일 줄 출력 (stdout), 나머지는 stderr")
    args = parser.parse_args()

    try:
        result = run(execute=args.execute, json_mode=args.json)
    except Exception as e:
        tb = traceback.format_exc()
        result = {
            "ok":               False,
            "ts":               now_iso(),
            "gateway_connected": False,
            "account":          None,
            "positions":        [],
            "exit_signals":     [],
            "entry_candidates": [],
            "universe_source":  "hardcoded",
            "error":            f"{e}\n{tb}",
        }

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        # 터미널 출력은 run() 내부 _p()가 이미 처리함
        if result.get("exit_signals"):
            print(f"\n★ EXIT 신호: {', '.join(result['exit_signals'])}")
        if not result["ok"]:
            print(f"\n[ERROR] {result.get('error', '')}", file=sys.stderr)
            sys.exit(1)
