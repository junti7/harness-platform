"""
IBKR TWS Paper Trading — Turtle Trading 자동화 (Phase B2)
ib_insync 기반. IB Gateway가 실행 중이어야 함.

Phase B2 (2026-06-27): core/turtle_strategy.py 통합.
  S1/S2 신호, 추세필터, 상관한도, heat cap, 피라미딩, 분산 sleeve,
  체결게이트, 상주손절, 고아/유령 reconcile.

실행:
  python scripts/ibkr_tws_paper_trader.py            # dry-run
  python scripts/ibkr_tws_paper_trader.py --execute  # 실제 paper 주문

전제조건:
  1. IB Gateway 실행 중 (페이퍼 계정 vvgfmt298 로그인)
  2. API 포트 4002 활성화 (IB Gateway > Configure > API > Settings)
"""

from __future__ import annotations

import argparse
import json
import sys
import time as _time
from datetime import datetime, timezone
from pathlib import Path

import asyncio
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")  # OS 환경변수 우선 (override 제거 — paper/live 포트 보호)

from ib_insync import IB, Stock, MarketOrder, StopOrder, util
from core.trading_universe import build_trading_universe, load_trading_universe, write_trading_universe
import core.turtle_strategy as core
from core.atomic_io import update_json_atomic

# ── 설정 ──────────────────────────────────────────────────────────────────────

TWS_HOST = "127.0.0.1"
import os as _os
IBKR_TRADING_MODE = _os.getenv("IBKR_TRADING_MODE", "paper").strip().lower()
TWS_PORT = 4002 if IBKR_TRADING_MODE == "paper" else 4001
TWS_CLIENT_ID = 10

LOG_PATH   = ROOT / "docs/reports/ibkr_tws_paper_log.jsonl"
STATE_PATH = ROOT / "docs/reports/ibkr_tws_positions.json"

TRADING_UNIVERSE_LOOKBACK_DAYS    = int(_os.getenv("TRADING_UNIVERSE_LOOKBACK_DAYS", "45"))
TRADING_UNIVERSE_MAX_SYMBOLS      = int(_os.getenv("TRADING_UNIVERSE_MAX_SYMBOLS", "24"))
TRADING_UNIVERSE_REFRESH_ON_RUN   = _os.getenv("TRADING_UNIVERSE_REFRESH_ON_RUN", "true").lower() == "true"

# 사이징/리스크 — core 단일 출처
TURTLE_STOP_MULT    = core.TURTLE_STOP_MULT
TURTLE_ATR_PERIOD   = core.TURTLE_ATR_PERIOD
TURTLE_RISK_PCT     = core.TURTLE_RISK_PCT
TURTLE_MAX_RISK_PCT = float(_os.getenv("PAPER_MAX_TRADE_RISK_PCT", "0.02"))

MAX_POSITIONS = int(_os.getenv("PAPER_TRADING_MAX_POSITIONS", "6"))

# 포트폴리오 heat 상한
PAPER_MAX_PORTFOLIO_HEAT = float(_os.getenv("PAPER_MAX_PORTFOLIO_HEAT", "0.10"))

# 상관 한도
MAX_UNITS_PER_GROUP = int(_os.getenv("PAPER_MAX_CORR_UNITS", "3"))

# 추세 필터
TREND_FILTER_ENABLED = _os.getenv("PAPER_TREND_FILTER", "true").lower() == "true"
TREND_MA_DAYS        = int(_os.getenv("PAPER_TREND_MA_DAYS", "100"))

# 피라미딩 (롱 전용)
PAPER_PYRAMID_ENABLED = _os.getenv("PAPER_PYRAMID_ENABLED", "true").lower() == "true"
PAPER_MAX_UNITS       = int(_os.getenv("PAPER_MAX_UNITS", "4"))
PAPER_PYRAMID_STEP_N  = float(_os.getenv("PAPER_PYRAMID_STEP_N", "0.5"))

# 분산 sleeve (측정 무상관: TLT +0.04, GLD -0.23, DBC +0.16, UUP +0.18 vs SMH)
PAPER_DIVERSIFY_ENABLED = _os.getenv("PAPER_DIVERSIFY_ENABLED", "true").lower() == "true"
DIVERSIFIERS_META = [
    {"symbol": "TLT", "exchange": "SMART", "currency": "USD", "region": "US",
     "name": "iShares 20+ Year Treasury Bond ETF", "harness_score": 0},
    {"symbol": "GLD", "exchange": "SMART", "currency": "USD", "region": "US",
     "name": "SPDR Gold Shares", "harness_score": 0},
    {"symbol": "DBC", "exchange": "SMART", "currency": "USD", "region": "US",
     "name": "Invesco DB Commodity Index ETF", "harness_score": 0},
    {"symbol": "UUP", "exchange": "SMART", "currency": "USD", "region": "US",
     "name": "Invesco DB US Dollar Index Bullish", "harness_score": 0},
]

# 체결 게이트
FILL_TIMEOUT_S = int(_os.getenv("PAPER_FILL_TIMEOUT_S", "90"))
FILL_POLL_S    = float(_os.getenv("PAPER_FILL_POLL_S", "3"))

# ── 외환 환율 (포지션 사이징 USD 환산용) ──────────────────────────────────────

import urllib.request as _urllib_req

_FOREX_FALLBACK: dict[str, float] = {
    "KRW": 1 / 1380,
    "JPY": 1 / 155,
    "TWD": 1 / 32,
    "HKD": 1 / 7.8,
    "USD": 1.0,
}
_forex_cache: dict[str, tuple[float, float]] = {}
_forex_source: dict[str, str] = {}
_FOREX_CACHE_TTL = 1800  # 30분


def get_usd_rate(ib: "IB | None", currency: str) -> float:
    """로컬 통화 1단위 → USD. 실시간 API → IBKR 전일종가 → 하드코딩 순 우선."""
    if currency == "USD":
        _forex_source["USD"] = "usd"
        return 1.0
    if currency in _forex_cache:
        rate, fetched_at = _forex_cache[currency]
        if _time.time() - fetched_at < _FOREX_CACHE_TTL:
            return rate
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        with _urllib_req.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        if data.get("result") == "success":
            now = _time.time()
            for cur, units_per_usd in data.get("rates", {}).items():
                if units_per_usd > 0:
                    _forex_cache[cur] = (1.0 / units_per_usd, now)
                    _forex_source[cur] = "live_api"
            if currency in _forex_cache:
                return _forex_cache[currency][0]
    except Exception:
        pass
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
                usd_per_local = 1.0 / bars[-1].close
                _forex_cache[currency] = (usd_per_local, _time.time())
                _forex_source[currency] = "ibkr_historical"
                return usd_per_local
        except Exception:
            pass
    rate = _FOREX_FALLBACK.get(currency, 1.0)
    _forex_cache[currency] = (rate, _time.time())
    _forex_source[currency] = "hardcoded"
    return rate


def usd_rate_is_reliable(currency: str) -> bool:
    return _forex_source.get(currency) in ("usd", "live_api", "ibkr_historical")


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def load_universe() -> list[dict]:
    if TRADING_UNIVERSE_REFRESH_ON_RUN:
        universe = build_trading_universe(
            domain="physical_ai",
            lookback_days=TRADING_UNIVERSE_LOOKBACK_DAYS,
            max_symbols=TRADING_UNIVERSE_MAX_SYMBOLS,
        )
        if universe:
            write_trading_universe(universe)
    from core.trading_universe import HARNESS_MIN_SCORE
    rows, _ = load_trading_universe(broker="ibkr", min_score=HARNESS_MIN_SCORE)
    return rows


def summarize_universe_drift(existing_symbols: set[str], tracked_symbols: set[str],
                              universe_symbols: set[str]) -> dict[str, list[str]]:
    return {
        "broker_positions_outside_universe": sorted(existing_symbols - universe_symbols),
        "tracked_positions_outside_universe": sorted(tracked_symbols - universe_symbols),
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_entry(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text())
            if not isinstance(state, dict):
                state = {}
            for _k in ("positions", "pending_orders"):
                if not isinstance(state.get(_k), dict):
                    state[_k] = {}
            return state
        except Exception:
            pass
    return {"positions": {}, "pending_orders": {}, "last_run": None}


# ── state 원자화 helpers ───────────────────────────────────────────────────────

def state_set_position(symbol: str, data: dict) -> None:
    def _m(s: dict) -> None:
        s.setdefault("positions", {})[symbol] = data
    update_json_atomic(STATE_PATH, _m)


def state_pop_position(symbol: str) -> None:
    def _m(s: dict) -> None:
        s.setdefault("positions", {}).pop(symbol, None)
    update_json_atomic(STATE_PATH, _m)


def state_set_last_run(ts: str) -> None:
    def _m(s: dict) -> None:
        s["last_run"] = ts
    update_json_atomic(STATE_PATH, _m)


def state_set_pending(symbol: str, data: dict) -> None:
    def _m(s: dict) -> None:
        s.setdefault("pending_orders", {})[symbol] = data
    update_json_atomic(STATE_PATH, _m)


def state_pop_pending(symbol: str) -> None:
    def _m(s: dict) -> None:
        s.setdefault("pending_orders", {}).pop(symbol, None)
    update_json_atomic(STATE_PATH, _m)


def state_flush_pending_and_positions(mem_state: dict) -> None:
    """reconcile 후 pending_orders + positions 전체를 원자적으로 flush."""
    def _m(s: dict) -> None:
        s["pending_orders"] = mem_state.get("pending_orders", {})
        s["positions"] = mem_state.get("positions", {})
    update_json_atomic(STATE_PATH, _m)


# ── IBKR bars 어댑터 ──────────────────────────────────────────────────────────

def ibkr_bars_to_core(bars) -> list[dict]:
    """ib_insync BarData → core.turtle_strategy 형식 {h,l,c,o}."""
    return [{"h": float(b.high), "l": float(b.low), "c": float(b.close), "o": float(b.open)}
            for b in bars]


def fetch_bars_ibkr(ib: IB, contract: Stock, days: int = 150) -> list[dict]:
    """IBKR 일봉 조회 → core 형식 반환. 실패 시 빈 리스트."""
    try:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=f"{days} D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )
        return ibkr_bars_to_core(bars) if bars else []
    except Exception as e:
        print(f"  [{getattr(contract, 'symbol', '?')}] bars 조회 실패: {e}")
        return []


# ── 체결 게이트 / 주문 취소 / 상주손절 ───────────────────────────────────────

def wait_for_fill_ibkr(ib: IB, trade,
                        timeout_s: int = FILL_TIMEOUT_S,
                        poll_s: float = FILL_POLL_S) -> tuple[str, float, float]:
    """체결 확인 게이트 — terminal 상태(Filled/Cancelled/Inactive/ApiCancelled)까지 폴링."""
    terminal = {"Filled", "Cancelled", "Inactive", "ApiCancelled"}
    deadline = _time.monotonic() + timeout_s
    while True:
        ib.sleep(poll_s)
        status = trade.orderStatus.status or ""
        if status in terminal or _time.monotonic() >= deadline:
            break
    fq = float(trade.orderStatus.filled or 0)
    fp = float(trade.orderStatus.avgFillPrice or 0)
    return trade.orderStatus.status or "Unknown", fq, fp


def cancel_ibkr_order(ib: IB, order_id: int | None) -> None:
    """IBKR 주문 취소 (이미 체결/소멸이면 무시)."""
    if not order_id:
        return
    try:
        for tr in ib.trades():
            if tr.order.orderId == order_id:
                ib.cancelOrder(tr.order)
                ib.sleep(1)
                return
    except Exception:
        pass


def place_resident_stop(ib: IB, contract: Stock, qty: int, stop_price: float,
                         account: str) -> int | None:
    """브로커에 GTC 손절 주문을 상주. 성공 시 orderId, 실패 시 None."""
    try:
        stop_order = StopOrder("SELL", qty, stop_price)
        stop_order.tif = "GTC"
        stop_order.account = account
        trade = ib.placeOrder(contract, stop_order)
        ib.sleep(1)
        return trade.order.orderId
    except Exception as e:
        print(f"  [{getattr(contract, 'symbol', '?')}] 상주손절 실패: {e}")
        return None


# ── 주문 생명주기 정합 (pending_orders) ───────────────────────────────────────

def reconcile_pending_orders(ib: IB, state: dict, paper_account: str) -> dict:
    """기존 pending_orders를 브로커 실상태와 대조해 정리.
    체결 → positions 승격, 취소/거절 → purge."""
    pending = state.get("pending_orders") or {}
    summary = {"promoted": [], "purged": [], "kept": [], "live_symbols": set()}
    if not pending:
        return summary

    try:
        broker_positions = {
            p.contract.symbol: p
            for p in ib.positions(account=paper_account)
            if abs(float(getattr(p, "position", 0) or 0)) > 0
        }
    except Exception:
        broker_positions = {}

    try:
        ib.reqAllOpenOrders()
        ib.sleep(1)
    except Exception:
        pass
    live_by_id: dict[int, str] = {}
    live_symbols: set[str] = set()
    try:
        for tr in ib.openTrades():
            o = getattr(tr, "order", None)
            st = getattr(tr, "orderStatus", None)
            con = getattr(tr, "contract", None)
            if o is None:
                continue
            oid = getattr(o, "orderId", None)
            status = (getattr(st, "status", "") if st is not None else "") or ""
            sym = (getattr(con, "symbol", "") if con is not None else "") or ""
            if oid is not None:
                live_by_id[oid] = status
            if sym:
                live_symbols.add(sym)
    except Exception:
        pass
    summary["live_symbols"] = live_symbols

    for sym in list(pending.keys()):
        meta = pending.get(sym)
        if not isinstance(meta, dict):
            pending.pop(sym, None)
            summary["purged"].append(sym)
            continue
        oid = meta.get("order_id")

        if sym in broker_positions:
            bp_item = broker_positions[sym]
            filled_qty = abs(float(getattr(bp_item, "position",
                                           meta.get("qty", 0)) or 0)) or meta.get("qty", 0)
            # pending → positions 승격 시 resident stop 발행 (없으면 무방비 방지)
            stop_val = meta.get("stop_loss")
            stop_id = None
            if stop_val and stop_val > 0 and int(filled_qty) > 0:
                try:
                    promo_contract = make_contract(sym, meta)
                    ib.qualifyContracts(promo_contract)
                    stop_id = place_resident_stop(ib, promo_contract, int(filled_qty),
                                                  stop_val, paper_account)
                except Exception:
                    pass
            promoted = {**meta, "status": "Filled", "qty": int(filled_qty),
                        "resident_stop_id": stop_id,
                        "filled_reconciled_at": now_iso()}
            state.setdefault("positions", {})[sym] = promoted
            pending.pop(sym, None)
            summary["promoted"].append(sym)
            log_entry({"ts": now_iso(), "action": "pending_filled_promoted", "symbol": sym,
                       "order_id": oid, "qty": filled_qty, "resident_stop_id": stop_id})
            continue

        if (oid in live_by_id) or (sym in live_symbols):
            meta["status"] = live_by_id.get(oid, meta.get("status")) or meta.get("status")
            summary["kept"].append(sym)
            continue

        pending.pop(sym, None)
        summary["purged"].append(sym)
        log_entry({"ts": now_iso(), "action": "pending_purged_stale", "symbol": sym,
                   "order_id": oid, "last_status": meta.get("status")})

    return summary


# ── 계약 생성 헬퍼 ────────────────────────────────────────────────────────────

def make_contract(sym: str, tracked: dict) -> Stock:
    """position record의 currency/exchange로 정확한 계약 생성 — 비USD 지원."""
    currency = tracked.get("currency", "USD") or "USD"
    exchange = tracked.get("exchange", "SMART") or "SMART"
    primary = exchange if exchange not in ("SMART", "", None) else ""
    return Stock(sym, "SMART", currency, primaryExchange=primary)


# ── 브로커 포지션 조회 ─────────────────────────────────────────────────────────

def get_broker_positions(ib: IB, paper_account: str) -> dict | None:
    """ib.portfolio() → {symbol: PortfolioItem}. API 실패 시 None (빈 dict와 구분)."""
    try:
        return {
            item.contract.symbol: item
            for item in ib.portfolio(account=paper_account)
            if abs(float(item.position or 0)) > 0
        }
    except Exception as e:
        print(f"  ❌ broker positions 조회 실패: {e}")
        return None


# ── reconcile + manage ────────────────────────────────────────────────────────

def reconcile_positions_ibkr(ib: IB, state: dict, broker_positions: dict,
                               universe_set: set, paper_account: str, dry_run: bool) -> list[dict]:
    """고아 입양 (브로커 O / state X) + 유령 정리 (브로커 X / state O)."""
    actions = []
    tracked_syms = set(state.get("positions", {}).keys())

    # 고아 입양: 브로커에는 있지만 state에 없는 유니버스 종목
    for sym, bp in broker_positions.items():
        if sym in tracked_syms or sym.upper() not in universe_set:
            continue
        # 브로커 계약에서 currency/exchange 읽기 (비USD 지원)
        bp_con = getattr(bp, "contract", None)
        currency = (getattr(bp_con, "currency", "USD") or "USD") if bp_con else "USD"
        exchange = (getattr(bp_con, "exchange", "SMART") or "SMART") if bp_con else "SMART"
        tracked_meta = {"currency": currency, "exchange": exchange}
        contract = make_contract(sym, tracked_meta)
        ib.qualifyContracts(contract)
        bars = fetch_bars_ibkr(ib, contract, days=TURTLE_ATR_PERIOD + 25)
        atr = core.compute_atr(bars) if len(bars) >= TURTLE_ATR_PERIOD + 1 else 0
        entry = float(getattr(bp, "averageCost", 0) or 0)
        qty = int(abs(float(getattr(bp, "position", 0) or 0)))
        stop = round(entry - TURTLE_STOP_MULT * atr, 2) if atr > 0 and entry > 0 else None
        stop_id = None
        resident_stop_missing = False
        if not dry_run and stop and stop > 0 and qty > 0:
            stop_id = place_resident_stop(ib, contract, qty, stop, paper_account)
            if stop_id is None:
                resident_stop_missing = True
                print(f"  ⚠️  [{sym}] 고아입양 상주손절 발행 실패 — resident_stop_missing=True")
                log_entry({"ts": now_iso(), "action": "adopt_orphan_stop_failed",
                           "symbol": sym, "qty": qty, "stop": stop})
        rec = {
            "entry_ts": now_iso(), "system": "S2",
            "entry_price": entry, "atr": atr, "stop_loss": stop,
            "qty": qty, "side": "buy",
            "resident_stop_id": stop_id, "adopted": True,
            "resident_stop_missing": resident_stop_missing,
            "currency": currency, "exchange": exchange,
        }
        if not dry_run:
            state_set_position(sym, rec)
        state.setdefault("positions", {})[sym] = rec
        act = {"ts": now_iso(), "action": "adopt_orphan", "symbol": sym,
               "stop_loss": stop, "qty": qty, "dry_run": dry_run,
               "resident_stop_id": stop_id}
        log_entry(act)
        actions.append(act)

    # 유령 정리: state에는 있지만 브로커에 없는 종목 (상주손절 발동/외부 청산)
    for sym in list(tracked_syms):
        if sym in broker_positions:
            continue
        tracked = state.get("positions", {}).get(sym, {})
        if not dry_run:
            cancel_ibkr_order(ib, tracked.get("resident_stop_id"))
            state_pop_position(sym)
        state.get("positions", {}).pop(sym, None)
        act = {"ts": now_iso(), "action": "ghost_reconcile", "symbol": sym,
               "dry_run": dry_run, "note": "state had position, broker did not"}
        log_entry(act)
        actions.append(act)

    return actions


def manage_positions_ibkr(ib: IB, state: dict, broker_positions: dict,
                           universe_set: set, paper_account: str, dry_run: bool) -> list[dict]:
    """reconcile + 손절/청산 관리."""
    actions = []
    actions.extend(reconcile_positions_ibkr(
        ib, state, broker_positions, universe_set, paper_account, dry_run))

    for sym in list(state.get("positions", {}).keys()):
        if sym not in broker_positions:
            continue
        tracked = state["positions"][sym]
        bp = broker_positions[sym]
        cp = float(getattr(bp, "marketPrice", 0) or 0)
        if not cp:
            cp = tracked.get("entry_price", 0)
        stop = tracked.get("stop_loss")
        system = tracked.get("system", "S2")
        qty = int(abs(float(getattr(bp, "position", tracked.get("qty", 0)) or 0)))

        reason = None

        # 손절 백업 체크 (1차 방어선은 상주손절)
        if stop and cp > 0 and cp <= stop:
            reason = f"stop_loss_hit (${cp:.2f} <= stop ${stop:.2f})"

        # 청산 신호 체크
        if not reason:
            contract = make_contract(sym, tracked)
            ib.qualifyContracts(contract)
            bars = fetch_bars_ibkr(ib, contract, days=35)
            if bars:
                triggered, msg = core.exit_signal(bars, system, side="long")
                if triggered:
                    reason = f"exit_signal: {msg}"

        if not reason:
            continue

        action = {"ts": now_iso(), "action": "exit", "symbol": sym,
                  "side": "sell", "qty": qty, "reason": reason,
                  "current_price": cp, "dry_run": dry_run}

        if not dry_run:
            try:
                cancel_ibkr_order(ib, tracked.get("resident_stop_id"))
                contract = make_contract(sym, tracked)
                ib.qualifyContracts(contract)
                order = MarketOrder("SELL", qty)
                order.tif = "GTC"
                order.account = paper_account
                trade = ib.placeOrder(contract, order)
                status, filled_qty, fill_price = wait_for_fill_ibkr(ib, trade)
                action["order_status"] = status
                action["filled_qty"] = filled_qty
                action["fill_price"] = fill_price
                action["status"] = "filled" if filled_qty > 0 else "not_filled"
                if filled_qty > 0:
                    state_pop_position(sym)
                    state.get("positions", {}).pop(sym, None)
            except Exception as e:
                action["status"] = "error"
                action["error"] = str(e)
        else:
            action["status"] = "dry_run"

        log_entry(action)
        actions.append(action)

    return actions


# ── 피라미딩 (롱 전용) ────────────────────────────────────────────────────────

def pyramid_positions_ibkr(ib: IB, state: dict, broker_positions: dict,
                            account_value: float, paper_account: str, dry_run: bool) -> list[dict]:
    """½N 유리 이동마다 유닛 추가 (최대 PAPER_MAX_UNITS). 롱 전용."""
    if not PAPER_PYRAMID_ENABLED:
        return []
    actions = []

    for sym, tracked in list(state.get("positions", {}).items()):
        if tracked.get("side") != "buy" or sym not in broker_positions:
            continue
        bp = broker_positions[sym]
        cp = float(getattr(bp, "marketPrice", 0) or 0)
        if not cp:
            continue

        pd = core.pyramid_decision(
            tracked, cp, account_value,
            enabled=PAPER_PYRAMID_ENABLED,
            max_units=PAPER_MAX_UNITS,
            step_n=PAPER_PYRAMID_STEP_N,
        )
        if pd is None:
            continue

        # heat 상한 확인 (기존 risk를 신규치로 교체 시 합산 heat)
        old_risk = tracked.get("risk_usd") or 0
        new_risk = pd["new_risk"]
        cur_heat = core.portfolio_heat(state.get("positions", {}), account_value)
        prospective_heat = cur_heat + (new_risk - old_risk) / account_value if account_value else 1.0
        if prospective_heat > PAPER_MAX_PORTFOLIO_HEAT:
            act = {"ts": now_iso(), "action": "pyramid_skip", "symbol": sym,
                   "reason": "heat_cap", "unit_to": pd["unit"]}
            log_entry(act)
            actions.append(act)
            continue

        action = {"ts": now_iso(), "action": "pyramid_add", "symbol": sym,
                  "unit": pd["unit"], "qty_add": pd["qty_add"],
                  "price": cp, "new_total_qty": pd["new_total"], "new_stop": pd["new_stop"],
                  "dry_run": dry_run}

        if not dry_run:
            try:
                contract = make_contract(sym, tracked)
                ib.qualifyContracts(contract)
                order = MarketOrder("BUY", pd["qty_add"])
                order.tif = "GTC"
                order.account = paper_account
                trade = ib.placeOrder(contract, order)
                status, filled_qty, fill_price = wait_for_fill_ibkr(ib, trade)
                action["order_status"] = status
                if filled_qty <= 0:
                    action["status"] = "not_filled"
                    log_entry(action)
                    actions.append(action)
                    continue
                fill_price = fill_price or cp
                N = pd["N"] or tracked.get("atr", 0)
                new_total = int(tracked.get("qty", 0)) + int(filled_qty)
                new_stop = round(fill_price - TURTLE_STOP_MULT * N, 2)
                new_risk = round(new_total * TURTLE_STOP_MULT * N, 2)
                # B1: 새 stop 먼저 발행 → 성공 확인 후 기존 stop 취소 (순서 역전)
                new_stop_id = place_resident_stop(ib, contract, new_total, new_stop, paper_account)
                if new_stop_id is None:
                    # 새 stop 실패 → 추가 유닛 즉시 시장가 청산
                    print(f"  ⚠️  [{sym}] 피라미딩 상주손절 실패 — 추가 {int(filled_qty)}주 즉시 청산")
                    rb_order = MarketOrder("SELL", int(filled_qty))
                    rb_order.tif = "GTC"
                    rb_order.account = paper_account
                    rb_trade = ib.placeOrder(contract, rb_order)
                    wait_for_fill_ibkr(ib, rb_trade)
                    action["status"] = "pyramid_stop_failed_reversed"
                    log_entry(action)
                    actions.append(action)
                    continue
                cancel_ibkr_order(ib, tracked.get("resident_stop_id"))  # 새 stop 성공 후 구 stop 취소
                updated = dict(tracked)
                updated.update({
                    "qty": new_total, "stop_loss": new_stop,
                    "last_unit_price": fill_price,
                    "unit_count": pd["unit"],
                    "resident_stop_id": new_stop_id,
                    "risk_usd": new_risk,
                })
                state_set_position(sym, updated)
                state["positions"][sym] = dict(updated)
                action.update({
                    "status": "filled", "fill_price": fill_price,
                    "new_total_qty": new_total, "new_stop": new_stop,
                    "resident_stop_id": new_stop_id,
                })
            except Exception as e:
                action["status"] = "error"
                action["error"] = str(e)
        else:
            action["status"] = "dry_run"
            sim = dict(tracked)
            sim.update({"qty": pd["new_total"], "stop_loss": pd["new_stop"],
                        "last_unit_price": cp, "unit_count": pd["unit"],
                        "risk_usd": pd["new_risk"]})
            state["positions"][sym] = sim

        log_entry(action)
        actions.append(action)

    return actions


# ── 메인 ──────────────────────────────────────────────────────────────────────

def run(execute: bool = False) -> None:
    dry_run = not execute
    universe = load_universe()
    if PAPER_DIVERSIFY_ENABLED:
        existing_syms = {row["symbol"] for row in universe}
        universe = universe + [d for d in DIVERSIFIERS_META if d["symbol"] not in existing_syms]

    universe = sorted(universe, key=lambda r: float(r.get("harness_score") or 0), reverse=True)
    universe_set = {row["symbol"].upper() for row in universe}

    print("=" * 62)
    print(f"IBKR TWS Paper Trader B2 — {'DRY RUN' if dry_run else '*** EXECUTE ***'}")
    print(f"실행시각: {now_iso()}")
    print(f"포트: {TWS_PORT} | 유니버스: {len(universe)}종목")
    print("=" * 62)

    ib = IB()
    try:
        ib.connect(TWS_HOST, TWS_PORT, clientId=TWS_CLIENT_ID, timeout=10)
    except Exception as e:
        print(f"[ERROR] IB Gateway 연결 실패: {e}")
        print("  → IB Gateway 실행 중인지, API 포트 4002 활성화됐는지 확인하세요.")
        return
    accounts = ib.managedAccounts()
    paper_account = next((a for a in accounts if a.startswith("DU")), accounts[0] if accounts else "")
    print(f"연결된 계좌: {accounts} | 사용: {paper_account}")

    nav_vals = ib.accountValues(account=paper_account)
    nav  = next((float(v.value) for v in nav_vals if v.tag == "NetLiquidation" and v.currency == "USD"), 0)
    cash = next((float(v.value) for v in nav_vals if v.tag == "TotalCashValue" and v.currency == "USD"), 0)
    print(f"NAV: ${nav:,.2f} | 현금: ${cash:,.2f}")

    state = load_state()
    state.setdefault("positions", {})
    state.setdefault("pending_orders", {})

    if not state.get("baseline"):
        state["baseline"] = {"nav": nav, "set_at": now_iso()}
        print(f"\n[베이스라인 설정] NAV ${nav:,.2f}")

    # pending_orders 정합 (이전 세션 잔여 처리)
    recon = reconcile_pending_orders(ib, state, paper_account)
    # B3: reconcile 결과(promoted positions + purged pending) 원자적 flush
    state_flush_pending_and_positions(state)
    if recon["promoted"] or recon["purged"] or recon["kept"]:
        print(f"\n[pending 정합] 승격={recon['promoted'] or '-'} | "
              f"유지={recon['kept'] or '-'} | 정리={recon['purged'] or '-'}")

    # 브로커 포지션 (marketPrice 포함) — 실패 시 ghost 오청산 방지를 위해 run 중단
    broker_positions = get_broker_positions(ib, paper_account)
    if broker_positions is None:
        print("[ERROR] 브로커 포지션 조회 실패 — 포지션 관리/신규 진입 전체 생략 (다음 run 재시도)")
        log_entry({"ts": now_iso(), "action": "run_aborted", "reason": "broker_positions_unavailable"})
        return
    pos_symbols = set(broker_positions.keys())
    tracked_symbols = set(state["positions"].keys())
    drift = summarize_universe_drift(pos_symbols, tracked_symbols, universe_set)
    print(f"\n현재 포지션: {pos_symbols or '없음'}")
    if drift["broker_positions_outside_universe"] or drift["tracked_positions_outside_universe"]:
        print(f"레거시 불일치: broker={drift['broker_positions_outside_universe'] or '-'} | "
              f"tracked={drift['tracked_positions_outside_universe'] or '-'}")

    # 포지션 관리 (reconcile + 손절/청산)
    print("\n── 포지션 관리 ──")
    mgmt_actions = manage_positions_ibkr(
        ib, state, broker_positions, universe_set, paper_account, dry_run)
    exit_acts = [a for a in mgmt_actions if a.get("action") == "exit"]
    recon_acts = [a for a in mgmt_actions if a.get("action") in ("adopt_orphan", "ghost_reconcile")]
    status_tag = "DRY-RUN" if dry_run else "실행"
    for a in recon_acts:
        if a["action"] == "adopt_orphan":
            print(f"  [{status_tag}] ADOPT {a['symbol']} — 고아입양 stop=${a.get('stop_loss')}")
        else:
            print(f"  [{status_tag}] GHOST {a['symbol']} — 유령정리")
    for a in exit_acts:
        print(f"  [{status_tag}] EXIT {a['symbol']} — {a['reason']}")
    if not mgmt_actions:
        print("  청산/정합 대상 없음")

    # 피라미딩
    print("\n── 피라미딩 ──")
    # 피라미딩 후 broker_positions 새로 고침
    broker_positions = get_broker_positions(ib, paper_account)
    pyramid_acts = pyramid_positions_ibkr(
        ib, state, broker_positions, nav, paper_account, dry_run)
    adds = [a for a in pyramid_acts if a.get("action") == "pyramid_add"]
    if adds:
        for a in adds:
            print(f"  [{status_tag}] PYRAMID {a['symbol']} 유닛{a['unit']}/{PAPER_MAX_UNITS} "
                  f"+{a['qty_add']}주 @${a['price']} → 총{a['new_total_qty']}주 stop=${a['new_stop']}")
    else:
        print("  추가 대상 없음")

    # 신호 스캔 전 broker snapshot 최신화 (manage/pyramid 반영)
    broker_positions = get_broker_positions(ib, paper_account) or {}
    pos_symbols = set(broker_positions.keys())

    print("\n── 신호 스캔 ──")
    entered = []

    for u_item in universe:
        sym      = u_item["symbol"]
        exchange = u_item.get("exchange", "SMART")
        currency = u_item.get("currency", "USD")
        region   = u_item.get("region", "US")
        name     = u_item.get("name", "")

        routing_exchange = "SMART"
        primary_exchange = exchange if exchange != routing_exchange else ""
        contract = Stock(sym, routing_exchange, currency, primaryExchange=primary_exchange)
        ib.qualifyContracts(contract)

        # bars 조회 (S2+2=57, ATR+1=21, MA+15=115 중 최대 → 150 여유 포함)
        bars = fetch_bars_ibkr(ib, contract, days=150)
        if not bars:
            print(f"  [{region}] {sym}: bars 없음")
            continue

        sig = core.signal_from_bars(sym, bars)
        if sig["signal"] == "insufficient_data":
            print(f"  [{region}] {sym}: 데이터 부족")
            continue

        signal    = sig["signal"]
        price     = sig["current_price"]
        atr       = sig["atr"]
        system    = sig.get("system")
        s2_high   = sig.get("s2_high", 0)
        dist      = (price - s2_high) / s2_high * 100 if s2_high else 0

        if signal != "breakout_long":
            curr_sym = {"KRW": "₩", "JPY": "¥", "TWD": "NT$", "HKD": "HK$"}.get(currency, "$")
            print(f"  [{region}] {sym}: 중립 {curr_sym}{price:.2f} | S2고점 {curr_sym}{s2_high:.2f}({dist:+.1f}%)")
            continue

        curr_sym = {"KRW": "₩", "JPY": "¥", "TWD": "NT$", "HKD": "HK$"}.get(currency, "$")
        print(f"\n  [{region}] {sym}({name}) {system} 브레이크아웃 @ {curr_sym}{price:.2f}")
        print(f"     S2고점={curr_sym}{s2_high:.2f}({dist:+.1f}%) ATR={atr:.4f}")

        # 중복 보유 체크
        if (sym in pos_symbols or sym in state["positions"]
                or sym in state["pending_orders"]):
            print(f"     → 이미 보유/대기 — 스킵")
            continue

        # 포지션 수 상한
        if len(state["positions"]) + len(state["pending_orders"]) >= MAX_POSITIONS:
            print(f"     → MAX_POSITIONS({MAX_POSITIONS}) 도달 — 대기")
            continue

        # 추세 필터 (F1)
        closes = [float(b.get("c", 0)) for b in bars if b.get("c")]
        trend_ok, trend_note = core.trend_filter_ok(
            closes, price, ma_days=TREND_MA_DAYS, enabled=TREND_FILTER_ENABLED)
        if not trend_ok:
            print(f"     → 추세필터 차단: {trend_note}")
            log_entry({"ts": now_iso(), "action": "trend_blocked", "symbol": sym,
                       "note": trend_note, "system": system})
            continue

        # 상관 한도 (F2)
        held = set(state.get("positions", {}).keys()) | pos_symbols
        blocked, block_reason = core.correlation_block(
            sym, held, max_units=MAX_UNITS_PER_GROUP)
        if blocked:
            print(f"     → 상관한도 차단: {block_reason}")
            log_entry({"ts": now_iso(), "action": "corr_blocked", "symbol": sym,
                       "note": block_reason, "system": system})
            continue

        # 환율 신뢰성 (해외 종목 사이징 오버 방지)
        usd_rate = get_usd_rate(ib, currency)
        if not usd_rate_is_reliable(currency):
            print(f"     → 환율 신뢰 불가({currency}, 하드코딩 폴백) — 스킵")
            log_entry({"ts": now_iso(), "action": "enter_blocked_fx_unreliable", "symbol": sym,
                       "currency": currency, "fx_source": _forex_source.get(currency, "unknown")})
            continue

        # TurtleGate — USD: core gate 직접 사용 / 비USD: USD ATR로 사이징, 현지통화로 stop
        atr_usd = atr * usd_rate
        if currency == "USD":
            gate = core.turtle_gate_check(sig, nav, TURTLE_MAX_RISK_PCT)
            shares    = gate["shares"]
            stop_loss = gate["stop_loss"]          # USD는 gate가 정확하게 계산
            risk_dollars = gate["risk_dollars"]
            risk_pct_val = gate["risk_pct"]
            gate_passed  = gate["passed"]
            gate_checks  = gate.get("checks", {})
        else:
            # 수량: USD 기준 ATR로 sizing (현지통화 ATR로 나누면 수량 왜곡)
            shares    = core.size_shares(nav, atr_usd)
            # 손절가: 현지통화 ATR 기준 (stop order는 현지통화로 제출)
            stop_loss = round(price - core.TURTLE_STOP_MULT * atr, 2)
            risk_dollars = round(shares * core.TURTLE_STOP_MULT * atr_usd, 2)
            risk_pct_val = round(risk_dollars / nav * 100, 3) if nav else 0
            gate_checks = {
                "signal":      sig["signal"] == "breakout_long",
                "atr":         atr > 0,
                "risk_pct":    risk_pct_val / 100 <= TURTLE_MAX_RISK_PCT * 1.05,
                "stop_loss":   stop_loss > 0,
                "exit_system": sig.get("system") in ("S1", "S2"),
            }
            gate_passed = all(gate_checks.values()) and shares > 0

        if shares <= 0:
            print(f"     → 수량 0 — 스킵")
            continue
        if not gate_passed:
            print(f"     → TurtleGate BLOCK: {gate_checks}")
            log_entry({"ts": now_iso(), "action": "gate_blocked", "symbol": sym,
                       "checks": gate_checks, "system": system})
            continue

        # 포트폴리오 heat 상한
        cur_heat = core.portfolio_heat(state.get("positions", {}), nav)
        new_heat = risk_dollars / nav if nav else 0
        if cur_heat + new_heat > PAPER_MAX_PORTFOLIO_HEAT:
            print(f"     → heat 초과 (현재 {cur_heat*100:.1f}% + 신규 {new_heat*100:.1f}% > {PAPER_MAX_PORTFOLIO_HEAT*100:.0f}%)")
            log_entry({"ts": now_iso(), "action": "heat_blocked", "symbol": sym,
                       "cur_heat": round(cur_heat, 4), "new_heat": round(new_heat, 4),
                       "cap": PAPER_MAX_PORTFOLIO_HEAT})
            continue

        pos_val_usd = round(shares * price * usd_rate, 2)
        print(f"     수량={shares}주 | 포지션≈${pos_val_usd:,.0f} | "
              f"손절={curr_sym}{stop_loss:.2f} | 리스크={risk_pct_val:.3f}% | heat↑{new_heat*100:.1f}%")

        if not dry_run:
            order = MarketOrder("BUY", shares)
            order.tif = "GTC"
            order.account = paper_account
            trade = ib.placeOrder(contract, order)

            # B4: 체결 확인 전 pending_orders 기록 (crash/timeout 복구 대비)
            pending_rec = {
                "order_id": trade.order.orderId,
                "qty": shares, "system": system,
                "entry_price": price, "stop_loss": stop_loss,
                "atr": atr, "currency": currency, "region": region,
                "exchange": exchange,  # 복구 시 make_contract에 사용
                "side": "buy", "status": "Submitted",
                "submitted_at": now_iso(),
            }
            state.setdefault("pending_orders", {})[sym] = pending_rec
            state_set_pending(sym, pending_rec)

            status, filled_qty, fill_price = wait_for_fill_ibkr(ib, trade)
            print(f"     체결: status={status} qty={filled_qty} avg=${fill_price:.2f}")

            if filled_qty <= 0:
                # timeout/미체결 — pending 유지하고 다음 run reconcile에 위임
                updated_pending = {**pending_rec, "status": status, "last_checked": now_iso()}
                state["pending_orders"][sym] = updated_pending
                state_set_pending(sym, updated_pending)
                print(f"     → 미체결/거절({status}) — pending 유지, 다음 run reconcile 처리")
                log_entry({"ts": now_iso(), "action": "enter_not_filled", "symbol": sym,
                           "order_status": status, "system": system, "dry_run": False})
                continue

            # 체결 완료 → pending 제거
            state_pop_pending(sym)
            state.get("pending_orders", {}).pop(sym, None)

            fill_price = fill_price or price
            actual_stop = round(fill_price - TURTLE_STOP_MULT * atr, 2)
            qty_i = int(filled_qty)

            # 상주손절 발행
            stop_id = place_resident_stop(ib, contract, qty_i, actual_stop, paper_account)

            # B1: 상주손절 실패 → 즉시 시장가 청산 (무방비 포지션 방지)
            if stop_id is None:
                print(f"     ⚠️  상주손절 발행 실패 — 즉시 청산 (gap-down 보호)")
                abort_order = MarketOrder("SELL", qty_i)
                abort_order.tif = "GTC"
                abort_order.account = paper_account
                abort_trade = ib.placeOrder(contract, abort_order)
                wait_for_fill_ibkr(ib, abort_trade)
                log_entry({"ts": now_iso(), "action": "enter_abort_stop_failed",
                           "symbol": sym, "qty": qty_i, "fill_price": fill_price,
                           "system": system})
                continue

            rec = {
                "entry_ts": now_iso(), "system": system,
                "entry_price": fill_price, "atr": atr, "stop_loss": actual_stop,
                "qty": qty_i, "side": "buy",
                "resident_stop_id": stop_id,
                "n_at_entry": atr,
                "last_unit_price": fill_price,
                "unit_count": 1,
                "risk_usd": round(qty_i * TURTLE_STOP_MULT * atr_usd, 2),
                "currency": currency, "region": region, "exchange": exchange,
            }
            state_set_position(sym, rec)
            state["positions"][sym] = dict(rec)

            log_entry({
                "ts": now_iso(), "action": "enter", "symbol": sym,
                "region": region, "currency": currency,
                "qty": qty_i, "fill_price": fill_price,
                "atr": atr, "atr_usd": round(atr_usd, 6),
                "stop_loss": actual_stop, "system": system,
                "resident_stop_id": stop_id,
                "risk_pct": gate["risk_pct"], "dry_run": False,
            })
            print(f"     → 진입 완료 (stop_id={stop_id}, stop=${actual_stop})")
        else:
            print(f"     → [DRY RUN] 매수 예정")
            log_entry({"ts": now_iso(), "action": "enter_dry_run", "symbol": sym,
                       "qty": shares, "price": price, "stop_loss": stop_loss,
                       "system": system, "dry_run": True})

        entered.append(sym)

    print(f"\n{'=' * 62}")
    print(f"완료 | 진입: {len(entered)}건 | 청산: {len(exit_acts)}건 | 유니버스: {len(universe)}종목")
    print(f"추적 포지션: {list(state['positions'].keys()) or '없음'}")
    print("=" * 62)

    # last_run + disconnect (finally 보장 — 예외 후에도 연결 해제)
    try:
        state_set_last_run(now_iso())
    finally:
        try:
            ib.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBKR TWS Paper Trader (B2)")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run(execute=args.execute)
