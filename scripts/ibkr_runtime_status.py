"""
IBKR 런타임 상태 확인 — B2 smoke test.

IB Gateway 연결, 계좌 인식, 포트폴리오 조회, paper state 일치 여부를 빠르게 점검한다.

실행:
  python scripts/ibkr_runtime_status.py
"""

from __future__ import annotations

import json
import sys
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
load_dotenv(ROOT / ".env", override=True)

import os as _os
from ib_insync import IB, Stock

TWS_HOST = "127.0.0.1"
IBKR_TRADING_MODE = _os.getenv("IBKR_TRADING_MODE", "paper").strip().lower()
TWS_PORT = 4002 if IBKR_TRADING_MODE == "paper" else 4001
TWS_CLIENT_ID = 99  # 전용 client ID (트레이더와 충돌 방지)

STATE_PATH = ROOT / "docs/reports/ibkr_tws_positions.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main() -> int:
    print("=" * 60)
    print(f"IBKR Runtime Status — {now_iso()}")
    print(f"모드: {IBKR_TRADING_MODE.upper()} | 포트: {TWS_PORT}")
    print("=" * 60)

    ok = True

    # 1. IB Gateway 연결
    print("\n[1] IB Gateway 연결")
    ib = IB()
    try:
        ib.connect(TWS_HOST, TWS_PORT, clientId=TWS_CLIENT_ID, timeout=10)
        print(f"  ✅ 연결 성공 (serverVersion={ib.client.serverVersion()})")
    except Exception as e:
        print(f"  ❌ 연결 실패: {e}")
        print("  → IB Gateway가 실행 중인지, 포트 4002 API 허용됐는지 확인")
        return 1

    # 2. 계좌 인식
    print("\n[2] 계좌 인식")
    accounts = ib.managedAccounts()
    if not accounts:
        print("  ❌ 계좌 없음 — 로그인 확인 필요")
        ok = False
    else:
        print(f"  ✅ 계좌: {accounts}")

    paper_account = next((a for a in accounts if a.startswith("DU")), accounts[0] if accounts else "")

    # 3. NAV 조회
    print("\n[3] NAV 조회")
    nav_vals = ib.accountValues(account=paper_account)
    nav = next((float(v.value) for v in nav_vals if v.tag == "NetLiquidation" and v.currency == "USD"), None)
    cash = next((float(v.value) for v in nav_vals if v.tag == "TotalCashValue" and v.currency == "USD"), None)
    if nav is None:
        print("  ❌ NAV 조회 실패")
        ok = False
    else:
        print(f"  ✅ NAV: ${nav:,.2f} | 현금: ${cash:,.2f}")

    # 4. 포트폴리오 조회
    print("\n[4] 포트폴리오 포지션")
    portfolio = ib.portfolio(account=paper_account)
    broker_syms = {item.contract.symbol for item in portfolio if abs(float(item.position or 0)) > 0}
    if broker_syms:
        for item in portfolio:
            if abs(float(item.position or 0)) > 0:
                print(f"  {item.contract.symbol}: {item.position}주 @ avgCost ${item.avgCost:.2f} | "
                      f"현재 ${item.marketPrice:.2f} | P&L ${item.unrealizedPNL:.2f}")
    else:
        print("  (포지션 없음)")

    # 5. state 파일과 대조
    print("\n[5] state 파일 대조")
    if not STATE_PATH.exists():
        print(f"  ℹ️  state 파일 없음: {STATE_PATH}")
    else:
        try:
            state = json.loads(STATE_PATH.read_text())
            tracked_syms = set((state.get("positions") or {}).keys())
            only_broker = broker_syms - tracked_syms
            only_state  = tracked_syms - broker_syms
            if not only_broker and not only_state:
                print(f"  ✅ 브로커 ↔ state 일치 ({len(tracked_syms)}개 포지션)")
            else:
                if only_broker:
                    print(f"  ⚠️  브로커에만 있음(고아): {sorted(only_broker)}")
                if only_state:
                    print(f"  ⚠️  state에만 있음(유령): {sorted(only_state)}")
        except Exception as e:
            print(f"  ❌ state 파싱 실패: {e}")

    # 6. bars 조회 smoke test (S&P ETF 대표 1종)
    print("\n[6] 시세 조회 smoke test (SPY)")
    try:
        contract = Stock("SPY", "SMART", "USD")
        ib.qualifyContracts(contract)
        bars = ib.reqHistoricalData(
            contract, endDateTime="", durationStr="5 D",
            barSizeSetting="1 day", whatToShow="TRADES",
            useRTH=True, formatDate=1,
        )
        if bars:
            print(f"  ✅ bars 조회 성공 ({len(bars)}봉) | 최근 종가 ${bars[-1].close:.2f}")
        else:
            print("  ⚠️  bars 빈 결과 (장 시간 외이거나 데이터 구독 확인)")
    except Exception as e:
        print(f"  ❌ bars 조회 실패: {e}")
        ok = False

    ib.disconnect()

    print(f"\n{'=' * 60}")
    status = "✅ ALL CLEAR — B2 실행 준비 완료" if ok else "❌ 일부 항목 실패 — 위 내용 확인 필요"
    print(status)
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
