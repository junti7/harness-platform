"""
Harness Trading Reset & Research Pipeline
2026-05-28 CEO 지시: 기존 포지션 전량 청산 → Harness 방식으로 새 종목 선정 → 0베이스 재시작

목적: Harness 리서치 파이프라인(Physical AI·AGI·Robotics·반도체) + Turtle Trading을
      순수하게 적용했을 때의 수익을 측정하기 위한 베이스라인 설정.

이 시점(2026-05-28)이 순수 실적 측정의 시작점이며, 이전 거래는 실적 산정에서 제외.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import requests

from scripts.alpaca_paper_trading import (
    ALPACA_KEY, ALPACA_SECRET, ALPACA_BASE_URL,
    get_account_summary, get_positions,
)

RESET_LOG_PATH = ROOT / "docs/trading/harness_reset_log.jsonl"
BASELINE_PATH  = ROOT / "docs/trading/harness_baseline_2026-05-28.json"

_HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
    "Content-Type": "application/json",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def cancel_all_open_orders() -> int:
    """미체결 주문 전량 취소. 청산 재시도 전 선행 필수."""
    url = f"{ALPACA_BASE_URL}/orders"
    r = requests.delete(url, headers=_HEADERS, timeout=15)
    cancelled = 0
    if r.ok:
        try:
            cancelled = len(r.json()) if r.text else 0
        except Exception:
            cancelled = 0
    return cancelled


def close_position(symbol: str) -> dict:
    url = f"{ALPACA_BASE_URL}/positions/{symbol}"
    r = requests.delete(url, headers=_HEADERS, timeout=15)
    if r.status_code in (200, 204):
        return {"ok": True, "symbol": symbol, "response": r.json() if r.text else {}}
    error_body = r.text[:300]
    # held_for_orders: 이미 매도 주문이 걸려 있음 → 매도 주문 이미 존재하는 것으로 처리
    if "held_for_orders" in error_body:
        return {"ok": True, "symbol": symbol, "note": "이미 매도 주문 대기 중 (held_for_orders) — 체결 대기"}
    return {"ok": False, "symbol": symbol, "status": r.status_code, "error": error_body}


def close_all_positions(positions: list[dict]) -> list[dict]:
    # 기존 미체결 주문 먼저 취소 (held_for_orders 방지)
    cancelled = cancel_all_open_orders()
    if cancelled:
        print(f"  미체결 주문 {cancelled}건 취소 완료 → 재청산 시도")
        import time; time.sleep(1)

    results = []
    for pos in positions:
        sym = pos["symbol"]
        result = close_position(sym)
        results.append(result)
        note = result.get("note", "")
        if result["ok"]:
            print(f"  ✅ {sym} 청산 {'완료' if not note else note}")
        else:
            print(f"  ❌ {sym} 청산 실패: {result.get('error', '')}")
    return results


def record_reset(pre_liquidation: dict, positions: list[dict], close_results: list[dict]) -> None:
    RESET_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "event": "harness_trading_reset",
        "timestamp": now_iso(),
        "reason": "CEO 지시 2026-05-28: Harness 방식 순수 실적 측정을 위한 0베이스 리셋. 이전 포지션(비리서치 기반)은 실적 산정 제외.",
        "performance_baseline_note": "이 시점 이후의 거래만 Harness 순수 실적으로 인정함. 이전 거래는 시스템 전환 이전 테스트로 분류.",
        "pre_liquidation_portfolio": pre_liquidation,
        "liquidated_positions": positions,
        "close_results": close_results,
    }
    with open(RESET_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"\n  리셋 이력 기록: {RESET_LOG_PATH}")


def record_baseline(post_liquidation: dict) -> None:
    baseline = {
        "harness_baseline": True,
        "version": "1.0",
        "established_at": now_iso(),
        "established_by": "CEO 지시 2026-05-28",
        "purpose": "Harness 리서치 파이프라인(Physical AI·AGI·Robotics·반도체) + Turtle Trading 순수 실적 측정 베이스라인",
        "starting_portfolio_value": post_liquidation.get("portfolio_value"),
        "starting_cash": post_liquidation.get("cash"),
        "starting_equity": post_liquidation.get("equity"),
        "performance_measurement_rule": "이 파일의 starting_portfolio_value를 기준으로 이후 모든 실적을 계산한다. 이전 손익(-$666.38 등)은 포함하지 않는다.",
        "method": {
            "layer1": "Harness DEEP RESEARCH 파이프라인 기반 종목 선정 (Physical AI·AGI·Robotics·반도체)",
            "layer2": "Turtle Trading System 1/2 진입 신호 + ATR 1% 포지션 사이징 + 2×ATR 손절",
        },
    }
    BASELINE_PATH.write_text(json.dumps(baseline, ensure_ascii=False, indent=2))
    print(f"  베이스라인 파일: {BASELINE_PATH}")


def main() -> None:
    print("=" * 60)
    print("Harness Trading Reset — 2026-05-28")
    print("CEO 지시: 전량 청산 후 0베이스 재시작")
    print("=" * 60)

    # 1. 청산 전 스냅샷
    print("\n[1] 현재 포트폴리오 스냅샷")
    pre = get_account_summary()
    positions = get_positions()
    print(f"  포트폴리오 가치: ${pre.get('portfolio_value'):,.2f}")
    print(f"  현금: ${pre.get('cash'):,.2f}")
    print(f"  총 손익: ${pre.get('total_pnl'):,.2f} ({pre.get('total_pnl_pct')}%)")
    print(f"  보유 종목: {[p['symbol'] for p in positions]}")

    if not positions:
        print("\n  보유 포지션 없음. 청산 불필요.")
        post = pre
    else:
        # 2. 전량 청산
        print(f"\n[2] 전량 청산 실행 ({len(positions)}개 종목)")
        close_results = close_all_positions(positions)

        # 3. 청산 후 잔고 확인
        import time
        time.sleep(3)
        post = get_account_summary()
        print(f"\n[3] 청산 후 잔고")
        print(f"  포트폴리오 가치: ${post.get('portfolio_value'):,.2f}")
        print(f"  현금: ${post.get('cash'):,.2f}")
        print(f"  매수 가능: ${post.get('buying_power'):,.2f}")

        # 4. 이력 기록
        record_reset(pre, positions, close_results)

    # 5. 베이스라인 기록
    print("\n[4] Harness 순수 실적 베이스라인 설정")
    record_baseline(post)

    print("\n" + "=" * 60)
    print(f"✅ 리셋 완료. Harness 순수 실적 측정 시작점: {now_iso()}")
    print(f"   시작 포트폴리오: ${post.get('portfolio_value'):,.2f}")
    print(f"   이후 거래는 Harness Layer1(리서치) → Layer2(Turtle) 순서로만 실행")
    print("=" * 60)


if __name__ == "__main__":
    main()
