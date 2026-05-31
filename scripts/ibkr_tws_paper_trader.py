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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

from ib_insync import IB, Stock, MarketOrder, util

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
UNIVERSE_PATH  = ROOT / "docs/trading/universe.json"

# Harness 리서치 유니버스 fallback (universe.json 없을 때 사용)
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
    # 한국
    {"region": "KR", "symbol": "000660", "exchange": "KRX",  "currency": "KRW", "name": "SK하이닉스",   "sector": "HBM Memory"},
    {"region": "KR", "symbol": "005930", "exchange": "KRX",  "currency": "KRW", "name": "삼성전자",     "sector": "Memory/Foundry"},
    {"region": "KR", "symbol": "042700", "exchange": "KRX",  "currency": "KRW", "name": "한미반도체",   "sector": "Chip Equip"},
    # 대만
    {"region": "TW", "symbol": "2330", "exchange": "TSEA", "currency": "TWD", "name": "TSMC",          "sector": "Foundry"},
    {"region": "TW", "symbol": "2454", "exchange": "TSEA", "currency": "TWD", "name": "MediaTek",      "sector": "SoC"},
    {"region": "TW", "symbol": "3711", "exchange": "TSEA", "currency": "TWD", "name": "ASE Technology","sector": "Packaging"},
    # 일본
    {"region": "JP", "symbol": "8035", "exchange": "TSE",  "currency": "JPY", "name": "Tokyo Electron","sector": "Chip Equip"},
    {"region": "JP", "symbol": "6861", "exchange": "TSE",  "currency": "JPY", "name": "Keyence",       "sector": "Factory Auto"},
    {"region": "JP", "symbol": "6954", "exchange": "TSE",  "currency": "JPY", "name": "FANUC",         "sector": "Robotics"},
    {"region": "JP", "symbol": "6723", "exchange": "TSE",  "currency": "JPY", "name": "Renesas Electronics","sector": "MCU/Auto Chip"},
    # 홍콩
    {"region": "HK", "symbol": "0700", "exchange": "SEHK", "currency": "HKD", "name": "Tencent",       "sector": "AI/Cloud"},
    {"region": "HK", "symbol": "0981", "exchange": "SEHK", "currency": "HKD", "name": "SMIC",          "sector": "Foundry"},
]

TURTLE_S2       = 55
TURTLE_ATR_DAYS = 20
TURTLE_STOP_MULT = 2.0
TURTLE_RISK_PCT  = 0.01   # 계좌 1%
MAX_POSITIONS    = 6

# ── 외환 환율 (포지션 사이징 USD 환산용) ──────────────────────────────────────

_FOREX_FALLBACK: dict[str, float] = {
    "KRW": 1 / 1380,
    "JPY": 1 / 155,
    "TWD": 1 / 32,
    "HKD": 1 / 7.8,
    "USD": 1.0,
}
_forex_cache: dict[str, float] = {}


def get_usd_rate(ib: "IB | None", currency: str) -> float:
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
                usd_per_local = 1.0 / bars[-1].close
                _forex_cache[currency] = usd_per_local
                return usd_per_local
        except Exception:
            pass
    _forex_cache[currency] = rate
    return rate


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def load_universe() -> list[dict]:
    """universe.json이 있으면 로드, 없으면 UNIVERSE_FALLBACK 사용."""
    if UNIVERSE_PATH.exists():
        try:
            data = json.loads(UNIVERSE_PATH.read_text())
            if isinstance(data, list) and len(data) > 0:
                return data
        except Exception:
            pass
    return UNIVERSE_FALLBACK


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
    return {"positions": {}, "last_run": None}


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

    if not state.get("baseline"):
        state["baseline"] = {"nav": nav, "set_at": now_iso()}
        print(f"\n[베이스라인 설정] NAV ${nav:,.2f}")

    # 현재 포지션
    positions = ib.positions(account=paper_account)
    pos_symbols = {p.contract.symbol for p in positions}
    print(f"\n현재 포지션: {pos_symbols or '없음'}")

    # 신호 스캔
    print("\n── 신호 스캔 ──")
    entered = []

    for u_item in universe:
        sym      = u_item["symbol"]
        exchange = u_item.get("exchange", "SMART")
        currency = u_item.get("currency", "USD")
        region   = u_item.get("region", "US")
        name     = u_item.get("name", "")

        contract = Stock(sym, exchange, currency)
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
            if sym in pos_symbols or sym in state["positions"]:
                print(f"     → 이미 보유 중 — 스킵")
                continue

            # 최대 포지션 수 초과
            if len(state["positions"]) >= MAX_POSITIONS:
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
                state["positions"][sym] = {
                    "entry_ts":    now_iso(),
                    "entry_price": price,
                    "atr":         atr,
                    "stop_loss":   stop_loss,
                    "qty":         shares,
                    "exchange":    exchange,
                    "currency":    currency,
                    "region":      region,
                }
                print(f"     → 주문 제출 (orderId={trade.order.orderId})")
                log_entry({
                    "ts": now_iso(), "action": "enter", "symbol": sym,
                    "region": region, "exchange": exchange, "currency": currency,
                    "qty": shares, "price": price,
                    "atr": atr, "atr_usd": round(atr_usd, 6),
                    "usd_rate": round(usd_rate, 8),
                    "stop_loss": stop_loss, "system": "S2",
                    "dry_run": False,
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
