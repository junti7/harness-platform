"""
Harness Layer 2 — Turtle Trading 신호 스캔
Harness 리서치 파이프라인(Layer 1) 선정 종목에 대해 Turtle 기술 신호를 검사한다.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

from scripts.alpaca_paper_trading import (
    get_turtle_signal, get_account_summary, TURTLE_RISK_PCT, TURTLE_STOP_MULT,
)

# Harness 리서치 파이프라인 선정 종목 (Layer 1 결과)
HARNESS_UNIVERSE = [
    ("NVDA", "Physical AI / AGI인프라", 9),
    ("AVGO", "AGI인프라 / 반도체",     9),
    ("TSM",  "반도체 파운드리",         9),
    ("MU",   "AI 메모리 반도체",        8),
    ("ANET", "AGI 네트워킹",            8),
    ("VRT",  "데이터센터 인프라",       8),
    ("TER",  "Robotics / 반도체 테스트",8),
    ("CRWV", "AI 특화 클라우드",        7),
    ("SYM",  "웨어하우스 자동화",       7),
    ("ISRG", "의료 로봇",               7),
    ("ROK",  "산업 자동화",             7),
]

SCAN_OUTPUT_PATH = ROOT / "docs/trading/harness_turtle_scan_2026-05-28.json"


def run_scan(account_value: float) -> dict:
    print("=" * 68)
    print("Harness Layer 2 — Turtle Trading 신호 스캔")
    print(f"스캔 시각: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"계좌 기준: ${account_value:,.0f}")
    print("=" * 68)

    results = []
    breakout_signals = []

    for ticker, sector, score in HARNESS_UNIVERSE:
        try:
            sig = get_turtle_signal(ticker)
        except Exception as e:
            print(f"  [ERR] {ticker}: {e}")
            continue

        price   = sig.get("current_price", 0)
        atr     = sig.get("atr", 0)
        signal  = sig.get("signal", "neutral")
        s1_high = sig.get("s1_high", 0)
        s2_high = sig.get("s2_high", 0)
        system  = sig.get("system", "")

        dist_s1 = ((price - s1_high) / s1_high * 100) if s1_high else 0
        dist_s2 = ((price - s2_high) / s2_high * 100) if s2_high else 0

        shares    = int((account_value * TURTLE_RISK_PCT) / atr) if atr > 0 else 0
        stop_loss = round(price - TURTLE_STOP_MULT * atr, 2) if signal == "breakout_long" else (
                    round(price + TURTLE_STOP_MULT * atr, 2) if signal == "breakout_short" else None)
        pos_value = round(shares * price, 2)
        risk_usd  = round(shares * atr, 2)
        risk_pct  = round(shares * atr / account_value * 100, 3) if account_value else 0

        tag = "🚀 BREAKOUT" if "breakout" in signal else "⏳ 중립   "
        print(
            f"{tag} [{ticker:5s}] ${price:8.2f} | ATR={atr:7.2f} "
            f"| S1고점={s1_high:8.2f}({dist_s1:+5.1f}%) "
            f"| S2고점={s2_high:8.2f}({dist_s2:+5.1f}%) "
            f"| 신호={signal}"
        )
        if "breakout" in signal:
            print(
                f"         → {system} 매수 {shares}주 | 포지션=${pos_value:,.0f} "
                f"| 손절=${stop_loss} | 리스크=${risk_usd:,.0f}({risk_pct}%)"
            )

        row = {
            "ticker":      ticker,
            "sector":      sector,
            "harness_score": score,
            "signal":      signal,
            "system":      system,
            "current_price": price,
            "atr":         atr,
            "s1_high":     s1_high,
            "s2_high":     s2_high,
            "dist_to_s1_pct": round(dist_s1, 2),
            "dist_to_s2_pct": round(dist_s2, 2),
            "suggested_shares": shares,
            "position_value":   pos_value,
            "stop_loss":   stop_loss,
            "risk_usd":    risk_usd,
            "risk_pct":    risk_pct,
        }
        results.append(row)
        if "breakout" in signal:
            breakout_signals.append(row)

    print()
    print(f"총 {len(results)}개 스캔 | 브레이크아웃 신호: {len(breakout_signals)}건")
    for b in breakout_signals:
        print(f"  ✅ {b['ticker']} {b['signal']} ({b['system']}) @ ${b['current_price']:.2f}")

    output = {
        "scan_at":         datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "account_value":   account_value,
        "total_scanned":   len(results),
        "breakout_count":  len(breakout_signals),
        "results":         results,
        "breakout_signals": breakout_signals,
    }

    SCAN_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCAN_OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n스캔 결과 저장: {SCAN_OUTPUT_PATH}")
    return output


if __name__ == "__main__":
    acc = get_account_summary()
    pv  = acc.get("portfolio_value", 99000)
    run_scan(pv)
