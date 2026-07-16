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
# Preserve launchd/container environment overrides used by trading guards.
load_dotenv(ROOT / ".env")

from scripts.alpaca_paper_trading import (
    get_turtle_signal, get_account_summary, TURTLE_RISK_PCT, TURTLE_STOP_MULT,
)
from core.trading_universe import load_trading_universe

# Layer 1 선정 종목은 **동적 universe.json**을 단일 출처로 한다(2026-06-10 통합).
# Alpaca는 US만 거래 가능 → broker="alpaca"로 US 종목만, harness_score ≥ 문턱만 채택.
# universe.json 부재/비어있으면 아래 정적 fallback(2026-05-28 수기 선정)을 쓴다.
# 문턱은 core.trading_universe.HARNESS_MIN_SCORE 단일 출처(IBKR·Alpaca 동일, 2026-06-21 통일).
from core.trading_universe import HARNESS_MIN_SCORE as _HARNESS_MIN_SCORE

# (ticker, company_name, sector, harness_score, selection_reason)
_STATIC_FALLBACK_META = [
    ("NVDA", "NVIDIA",              "Physical AI / AGI인프라",  9,
     "AI 가속기 80-90% 점유율. Isaac GR00T·Cosmos로 로봇 OS 표준화 중. 2026 로보틱스 매출 YoY +72%."),
    ("AVGO", "Broadcom",            "AGI인프라 / 반도체",       9,
     "커스텀 AI ASIC 1위. FY2026 Q1 AI칩 매출 YoY +106%. $73B 수주 잔고. Anthropic TPU 공급."),
    ("TSM",  "TSMC",                "반도체 파운드리",          9,
     "AI칩 유일한 2nm 첨단 파운드리. 2026 Q1 매출 YoY +35%, 마진 66.2%. 대체 불가 병목 자산."),
    ("MU",   "Micron",              "AI 메모리 반도체",         8,
     "HBM3E 전량 완판·HBM4 NVDA Vera Rubin 공급. FY26Q2 EPS $12.07 사상 최대. 시총 $1T 달성."),
    ("ANET", "Arista Networks",     "AGI 네트워킹",             8,
     "AI 데이터센터 고속 이더넷 스위칭 1위. AI 네트워킹 매출 가이던스 $3.25B. GPU간 통신 필수 인프라."),
    ("VRT",  "Vertiv",              "데이터센터 전력·냉각",     8,
     "AI 데이터센터 냉각·전력 인프라 1위. NVDA와 차세대 전력 아키텍처 공동 개발 파트너."),
    ("TER",  "Teradyne",            "Robotics / 반도체 테스트", 8,
     "반도체 테스트 장비 1위 + Universal Robots 자회사. Q1 매출 YoY +87%. AI칩 테스트 수요 구조적 성장."),
    ("CRWV", "CoreWeave",           "AI 특화 클라우드",         7,
     "AI 전용 클라우드 순수 플레이. $66B 수주 잔고. Meta $21B 장기 계약. 2026 매출 가이던스 $12-13B."),
    ("SYM",  "Symbotic",            "웨어하우스 자동화 Robotics",7,
     "창고 완전 자동화 1위. FY2026 Q1 GAAP 첫 흑자 전환. 월마트·C&S 배치 진행 중."),
    ("ISRG", "Intuitive Surgical",  "의료 로봇",                7,
     "다빈치 수술 로봇 세계 독점. 구독형 소모품 수익 구조. 다빈치 5세대 + AI 수술 보조 확장 중."),
    ("ROK",  "Rockwell Automation", "산업 자동화",              7,
     "미국 리쇼어링 수혜 1위. 인더스트리 4.0 + AI 예측 유지보수. YTD +32.2%. 목표가 $480-525."),
]


def load_harness_universe_meta(min_score: int = _HARNESS_MIN_SCORE, broker: str = "alpaca") -> list[tuple]:
    """동적 universe.json에서 (ticker, name, sector, harness_score, selection_reason) 튜플 목록.

    broker로 거래 가능 시장 필터(alpaca=US). harness_score ≥ min_score만.
    universe.json 부재/비어있으면 정적 fallback(_STATIC_FALLBACK_META). 동적 결과가 비면 fallback.
    """
    rows, source = load_trading_universe(broker=broker)
    if source == "fallback":
        return list(_STATIC_FALLBACK_META)
    meta: list[tuple] = []
    for r in rows:
        # belt-and-suspenders(Red Team Codex#2): alpaca는 US만 — brokers 필드 외에 region도 확인.
        if broker == "alpaca" and str(r.get("region", "")).upper() not in ("US", ""):
            continue
        try:
            score = int(r.get("harness_score", 0) or 0)
        except (TypeError, ValueError):
            score = 0
        if score < min_score:
            continue
        reason = (r.get("selection_reason_ko") or r.get("selection_reason") or "")[:300]
        meta.append((r["symbol"], r.get("name", r["symbol"]), r.get("sector", ""), score, reason))
    return meta or list(_STATIC_FALLBACK_META)


# Layer 1 동적 유니버스(단일 출처). 정적 _STATIC_FALLBACK_META는 universe.json 없을 때만.
HARNESS_UNIVERSE_META = load_harness_universe_meta()
# 하위 호환 (tuple 슬라이싱용)
HARNESS_UNIVERSE = [(t, s, sc) for t, _, s, sc, _ in HARNESS_UNIVERSE_META]

SCAN_OUTPUT_PATH = ROOT / "docs/trading/harness_turtle_scan_2026-05-28.json"


def run_scan(account_value: float) -> dict:
    print("=" * 68)
    print("Harness Layer 2 — Turtle Trading 신호 스캔")
    print(f"스캔 시각: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    print(f"계좌 기준: ${account_value:,.0f}")
    print("=" * 68)

    results = []
    breakout_signals = []

    for ticker, company_name, sector, score, selection_reason in HARNESS_UNIVERSE_META:
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
            f"{tag} [{ticker:5s}({company_name})] ${price:8.2f} | ATR={atr:7.2f} "
            f"| S2고점={s2_high:8.2f}({dist_s2:+5.1f}%) | 신호={signal}"
        )
        if "breakout" in signal:
            print(
                f"         → {system} 매수 {shares}주 | 포지션=${pos_value:,.0f} "
                f"| 손절=${stop_loss} | 리스크=${risk_usd:,.0f}({risk_pct}%)"
            )
            print(f"         선정 사유: {selection_reason[:80]}")

        row = {
            "ticker":           ticker,
            "company_name":     company_name,
            "selection_reason": selection_reason,
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
