"""
IBKR TWS Paper Trading — Turtle Trading 자동화
ib_insync 기반. TWS가 실행 중이어야 함 (포트 7497, 페이퍼 트레이딩).

실행:
  python scripts/ibkr_tws_paper_trader.py            # dry-run
  python scripts/ibkr_tws_paper_trader.py --execute  # 실제 paper 주문

전제조건:
  1. TWS 실행 중 (페이퍼 계정 vvgfmt298 로그인)
  2. TWS > Edit > Global Configuration > API > Settings
     - Enable ActiveX and Socket Clients: ✅
     - Socket port: 7497
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
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
load_dotenv(ROOT / ".env", override=True)

from ib_insync import IB, Stock, MarketOrder, util
from core.trading_universe import build_trading_universe, load_trading_universe, write_trading_universe

# ── 설정 ──────────────────────────────────────────────────────────────────────

TWS_HOST = "127.0.0.1"
# IBKR_TRADING_MODE=paper → 4002 (IB Gateway 페이퍼)
# IBKR_TRADING_MODE=live  → 4001 (IB Gateway 실전)
import os as _os
IBKR_TRADING_MODE = _os.getenv("IBKR_TRADING_MODE", "paper").strip().lower()
TWS_PORT = 4002 if IBKR_TRADING_MODE == "paper" else 4001
TWS_CLIENT_ID = 10       # 임의 클라이언트 ID (충돌 방지)

LOG_PATH       = ROOT / "docs/reports/ibkr_tws_paper_log.jsonl"
STATE_PATH     = ROOT / "docs/reports/ibkr_tws_positions.json"
TRADING_UNIVERSE_LOOKBACK_DAYS = int(_os.getenv("TRADING_UNIVERSE_LOOKBACK_DAYS", "45"))
TRADING_UNIVERSE_MAX_SYMBOLS = int(_os.getenv("TRADING_UNIVERSE_MAX_SYMBOLS", "24"))
TRADING_UNIVERSE_REFRESH_ON_RUN = _os.getenv("TRADING_UNIVERSE_REFRESH_ON_RUN", "true").lower() == "true"
# UNIVERSE_FALLBACK 제거 — core/trading_universe.py의 _load_seed_registry()가 단일 소스

TURTLE_S2       = 55
TURTLE_ATR_DAYS = 20
TURTLE_STOP_MULT = 2.0
TURTLE_RISK_PCT  = 0.01   # 계좌 1%
MAX_POSITIONS    = 6

# ── 외환 환율 (포지션 사이징 USD 환산용) ──────────────────────────────────────

import time as _time
import urllib.request as _urllib_req

_FOREX_FALLBACK: dict[str, float] = {
    "KRW": 1 / 1380,
    "JPY": 1 / 155,
    "TWD": 1 / 32,
    "HKD": 1 / 7.8,
    "USD": 1.0,
}
# 캐시: currency → (usd_per_local, fetched_at_epoch)
_forex_cache: dict[str, tuple[float, float]] = {}
# 환율 출처 추적: currency → "live_api" | "ibkr_historical" | "hardcoded" | "usd"
# 포지션 사이징에서 "hardcoded"(근사값)일 때 해외 진입을 차단하기 위해 사용(over-sizing 방지).
_forex_source: dict[str, str] = {}
_FOREX_CACHE_TTL = 1800  # 30분


def get_usd_rate(ib: "IB | None", currency: str) -> float:
    """
    로컬 통화 1단위 → USD 반환. 절대 예외 없음.
    우선순위: open.er-api.com 실시간 → IBKR 전일 종가 → 하드코딩 근사값
    출처는 _forex_source에 기록(usd_rate_is_reliable로 신뢰성 판정).
    """
    if currency == "USD":
        _forex_source["USD"] = "usd"
        return 1.0

    # 캐시 확인 (30분 TTL) — 출처는 이미 기록돼 있음
    if currency in _forex_cache:
        rate, fetched_at = _forex_cache[currency]
        if _time.time() - fetched_at < _FOREX_CACHE_TTL:
            return rate

    # 1순위: 실시간 환율 API (전체 통화 한 번에 캐시)
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

    # 2순위: IBKR 전일 종가
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

    # 3순위: 하드코딩 fallback (근사값 — 사이징 신뢰 불가)
    rate = _FOREX_FALLBACK.get(currency, 1.0)
    _forex_cache[currency] = (rate, _time.time())
    _forex_source[currency] = "hardcoded"
    return rate


def usd_rate_is_reliable(currency: str) -> bool:
    """포지션 사이징에 쓸 만큼 환율이 신뢰 가능한가. 하드코딩 근사값이면 False.
    USD(1.0)·실시간 API·IBKR 전일종가는 신뢰. get_usd_rate 호출 *후* 확인한다."""
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
    rows, _ = load_trading_universe(broker="ibkr")
    return rows


def summarize_universe_drift(existing_symbols: set[str], tracked_symbols: set[str], universe_symbols: set[str]) -> dict[str, list[str]]:
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
            state.setdefault("positions", {})
            state.setdefault("pending_orders", {})
            return state
        except Exception:
            pass
    return {"positions": {}, "pending_orders": {}, "last_run": None}


def save_state(s: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(s, indent=2, ensure_ascii=False))


# ── 가격 히스토리 + Turtle 계산 ───────────────────────────────────────────────

def calc_turtle_signal(ib: IB, contract: Stock) -> dict | None:
    """55일 최고가 브레이크아웃 + 20일 ATR 계산"""
    try:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr="90 D",
            barSizeSetting="1 day",
            whatToShow="TRADES",
            useRTH=True,
            formatDate=1,
        )
        if not bars or len(bars) < TURTLE_S2 + 2:
            return None

        closes = [b.close for b in bars]
        highs  = [b.high  for b in bars]
        lows   = [b.low   for b in bars]

        current_price = closes[-1]

        # S2 진입: 55일 최고가 돌파
        s2_high = max(highs[-TURTLE_S2 - 1:-1])
        signal  = "breakout_long" if current_price > s2_high else "neutral"

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

        return {
            "symbol":        contract.symbol,
            "current_price": round(current_price, 2),
            "s2_high":       round(s2_high, 2),
            "atr":           round(atr, 4),
            "signal":        signal,
        }
    except Exception as e:
        print(f"  [{contract.symbol}] 신호 계산 실패: {e}")
        return None


# ── 메인 ──────────────────────────────────────────────────────────────────────

def run(execute: bool = False) -> None:
    dry_run = not execute
    universe = load_universe()
    # Finding 3(Red Team 2026-06-10): MAX_POSITIONS 한도가 선착순으로 채워져 저점수 종목이
    # 슬롯을 선점하는 문제 방지. 진입 후보를 harness_score 내림차순으로 정렬해 *동일 스캔에서
    # 동시 돌파* 시 고확신 종목이 한정 슬롯을 먼저 차지하게 한다.
    # (Turtle 원칙 준수: 기존 보유 포지션을 점수로 교체하지 않음 — 진입 우선순위만 조정)
    universe = sorted(universe, key=lambda r: float(r.get("harness_score") or 0), reverse=True)

    print("=" * 62)
    print(f"IBKR TWS Paper Trader — {'DRY RUN' if dry_run else '*** EXECUTE ***'}")
    print(f"실행시각: {now_iso()}")
    print(f"포트: {TWS_PORT} (페이퍼 트레이딩)")
    print(f"유니버스: {len(universe)}종목")
    print("=" * 62)

    ib = IB()
    try:
        ib.connect(TWS_HOST, TWS_PORT, clientId=TWS_CLIENT_ID, timeout=10)
    except Exception as e:
        print(f"[ERROR] TWS 연결 실패: {e}")
        print("  → IB Gateway가 실행 중인지, API 포트 4002가 활성화됐는지 확인하세요.")
        return

    # 계좌 확인
    accounts = ib.managedAccounts()
    paper_account = next((a for a in accounts if a.startswith("DU")), accounts[0] if accounts else "")
    print(f"연결된 계좌: {accounts} | 사용: {paper_account}")

    nav_vals = ib.accountValues(account=paper_account)
    nav = next((float(v.value) for v in nav_vals if v.tag == "NetLiquidation" and v.currency == "USD"), 0)
    cash = next((float(v.value) for v in nav_vals if v.tag == "TotalCashValue" and v.currency == "USD"), 0)
    print(f"NAV: ${nav:,.2f} | 현금: ${cash:,.2f}")

    state = load_state()
    state.setdefault("positions", {})
    state.setdefault("pending_orders", {})

    if not state.get("baseline"):
        state["baseline"] = {"nav": nav, "set_at": now_iso()}
        print(f"\n[베이스라인 설정] NAV ${nav:,.2f}")

    # 현재 포지션
    positions = ib.positions(account=paper_account)
    pos_symbols = {p.contract.symbol for p in positions}
    managed_symbols = set(state["positions"].keys()) | set(state["pending_orders"].keys())
    drift = summarize_universe_drift(pos_symbols, managed_symbols, {row["symbol"] for row in universe})
    print(f"\n현재 포지션: {pos_symbols or '없음'}")
    if drift["broker_positions_outside_universe"] or drift["tracked_positions_outside_universe"]:
        print(f"레거시 포지션 불일치: broker={drift['broker_positions_outside_universe'] or '-'} | tracked={drift['tracked_positions_outside_universe'] or '-'}")

    # 신호 스캔
    print("\n── 신호 스캔 ──")
    entered = []

    for u_item in universe:
        sym      = u_item["symbol"]
        exchange = u_item.get("exchange", "SMART")
        currency = u_item.get("currency", "USD")
        region   = u_item.get("region", "US")
        name     = u_item.get("name", "")

        routing_exchange = "SMART"
        primary_exchange = exchange if routing_exchange != exchange else ""
        contract = Stock(sym, routing_exchange, currency, primaryExchange=primary_exchange)
        ib.qualifyContracts(contract)
        sig = calc_turtle_signal(ib, contract)

        if sig is None:
            print(f"  [{region}] {sym}: 데이터 부족")
            continue

        signal  = sig["signal"]
        price   = sig["current_price"]
        atr     = sig["atr"]
        s2_high = sig["s2_high"]
        dist    = (price - s2_high) / s2_high * 100

        if signal == "breakout_long":
            # 포지션 사이징: ATR을 USD로 환산 후 계좌 1% 리스크 기준
            usd_rate = get_usd_rate(ib, currency)
            # Fail-safe(Red Team 2026-06-10 Infra 2): 해외 통화 환율이 하드코딩 근사값으로
            # 폴백된 상태면 사이징이 틀려 1% 리스크 한도를 초과할 수 있다(over-sizing).
            # Turtle Never 규칙(단일 트레이드 리스크 1% 초과 금지)에 따라 진입을 차단한다.
            if not usd_rate_is_reliable(currency):
                print(f"     → ⚠️ 환율 신뢰 불가({currency}, 하드코딩 폴백) — 사이징 부정확 위험으로 진입 차단(스킵)")
                log_entry({
                    "ts": now_iso(), "action": "enter_blocked_fx_unreliable", "symbol": sym,
                    "region": region, "currency": currency, "price": price, "atr": atr,
                    "usd_rate": round(usd_rate, 8), "fx_source": _forex_source.get(currency, "unknown"), "system": "S2",
                })
                continue
            atr_usd  = atr * usd_rate
            shares   = int((nav * TURTLE_RISK_PCT) / atr_usd) if atr_usd > 0 else 0
            stop_loss = round(price - TURTLE_STOP_MULT * atr, 2)
            pos_val_local = round(shares * price, 2)
            pos_val_usd   = round(shares * price * usd_rate, 2)

            curr_sym = {"KRW": "₩", "JPY": "¥", "TWD": "NT$", "HKD": "HK$"}.get(currency, "$")
            print(f"\n  [{region}] {sym}({name}) S2 브레이크아웃 @ {curr_sym}{price:.2f}")
            print(f"     S2고점={curr_sym}{s2_high:.2f}({dist:+.1f}%) ATR={atr:.2f}{currency} (${atr_usd:.4f}) 수량={shares}주")
            print(f"     포지션={curr_sym}{pos_val_local:,.0f} (≈${pos_val_usd:,.0f}) 손절={curr_sym}{stop_loss:.2f}")

            # 이미 보유 중이면 스킵
            if sym in pos_symbols or sym in state["positions"] or sym in state["pending_orders"]:
                print(f"     → 이미 보유 중 — 스킵")
                continue

            # 최대 포지션 수 초과
            if len(state["positions"]) + len(state["pending_orders"]) >= MAX_POSITIONS:
                print(f"     → MAX_POSITIONS({MAX_POSITIONS}) 도달 — 대기")
                continue

            if shares <= 0:
                print(f"     → 수량 0 — 스킵")
                continue

            if not dry_run:
                order = MarketOrder("BUY", shares)
                order.tif = "GTC"  # 장 마감 후에도 유효 (DAY 자동설정 방지)
                trade = ib.placeOrder(contract, order)
                ib.sleep(2)
                status = (trade.orderStatus.status or "").lower()
                if status in {"cancelled", "inactive", "apicancelled"}:
                    print(f"     → 주문 거절/취소 ({trade.order.orderId}, status={trade.orderStatus.status})")
                    log_entry({
                        "ts": now_iso(), "action": "enter_rejected", "symbol": sym,
                        "region": region, "exchange": exchange, "currency": currency,
                        "qty": shares, "price": price, "status": trade.orderStatus.status,
                        "atr": atr, "atr_usd": round(atr_usd, 6), "usd_rate": round(usd_rate, 8),
                        "stop_loss": stop_loss, "system": "S2", "dry_run": False,
                    })
                    continue
                target_bucket = "positions" if status == "filled" else "pending_orders"
                state[target_bucket][sym] = {
                    "entry_ts": now_iso(),
                    "entry_price": price,
                    "atr": atr,
                    "stop_loss": stop_loss,
                    "qty": shares,
                    "exchange": routing_exchange,
                    "currency": currency,
                    "region": region,
                    "order_id": trade.order.orderId,
                    "status": trade.orderStatus.status,
                }
                print(f"     → 주문 제출 (orderId={trade.order.orderId}, status={trade.orderStatus.status}, bucket={target_bucket})")
                log_entry({
                    "ts": now_iso(), "action": "enter", "symbol": sym,
                    "region": region, "exchange": routing_exchange, "currency": currency,
                    "qty": shares, "price": price,
                    "atr": atr, "atr_usd": round(atr_usd, 6),
                    "usd_rate": round(usd_rate, 8),
                    "stop_loss": stop_loss, "system": "S2",
                    "dry_run": False, "status": trade.orderStatus.status, "bucket": target_bucket,
                })
            else:
                print(f"     → [DRY RUN] 매수 예정")
            entered.append(sym)
        else:
            curr_sym = {"KRW": "₩", "JPY": "¥", "TWD": "NT$", "HKD": "HK$"}.get(currency, "$")
            print(f"  [{region}] {sym}: 중립 {curr_sym}{price:.2f} | S2고점 {curr_sym}{s2_high:.2f}({dist:+.1f}%)")

    state["last_run"] = now_iso()
    save_state(state)
    ib.disconnect()

    print(f"\n{'=' * 62}")
    print(f"완료 | 진입: {len(entered)}건 | 유니버스: {len(universe)}종목")
    print("=" * 62)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IBKR TWS Paper Trader")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run(execute=args.execute)
