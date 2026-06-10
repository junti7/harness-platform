#!/usr/bin/env python3
"""가격 피드 정밀도 오디트 — Alpaca vs Yahoo(vs IBKR) Turtle 입력값 편차 측정.

배경(Red Team 2026-06-10 Finding 2): Alpaca 기반 자동매매와 IBKR/Yahoo 기반 모니터가
서로 다른 가격 제공처를 쓰면, 같은 종목·같은 Turtle 규칙에도 current_price·ATR·돌파선(S1/S2)이
달라 신호/포지션 괴리(Drift)가 생긴다. 이 스크립트는 *읽기 전용*으로 두(또는 세) 피드의
Turtle 입력값을 나란히 계산해 편차를 보고한다. 거래 로직은 일절 건드리지 않는다.

사용:
  .venv/bin/python scripts/audit_price_feed_precision.py            # 사람용 표
  .venv/bin/python scripts/audit_price_feed_precision.py --json     # JSON 한 줄
  .venv/bin/python scripts/audit_price_feed_precision.py --ibkr     # IBKR 라이브 피드 포함(게이트웨이 필요)

판정: 종목별 ATR·S2고점 상대편차가 임계값(기본 1.0%)을 넘으면 ⚠️, 돌파 신호 불일치는 🚨.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

# 재사용: Alpaca 신호(alpaca_paper_trading) + Yahoo 신호(ibkr_turtle_monitor)
from scripts.alpaca_paper_trading import get_turtle_signal as _alpaca_signal  # noqa: E402
from scripts.ibkr_turtle_monitor import (  # noqa: E402
    _fetch_yahoo_daily_bars,
    _compute_signal_from_bars,
    calc_full_signal,
)
from core.trading_universe import load_trading_universe  # noqa: E402

# ATR·S2고점 상대편차가 이 비율을 넘으면 경고
ATR_DRIFT_WARN_PCT = 1.0
PRICE_DRIFT_WARN_PCT = 1.0


def _pct_delta(a: float | None, b: float | None) -> float | None:
    """기준 a 대비 b의 상대 편차(%) — |a-b|/|a| * 100. 값이 없으면 None."""
    if a is None or b is None or a == 0:
        return None
    return round(abs(a - b) / abs(a) * 100, 3)


def _yahoo_symbol(sym: str, region: str) -> str:
    r = region.upper()
    if r == "KR":
        return f"{sym}.KS"
    if r == "JP":
        return f"{sym}.T"
    if r == "TW":
        return f"{sym}.TW"
    if r == "HK":
        return f"{sym}.HK"
    return sym


def _yahoo_signal(sym: str, region: str) -> dict | None:
    try:
        bars = _fetch_yahoo_daily_bars(_yahoo_symbol(sym, region))
        if not bars:
            return None
        return _compute_signal_from_bars(sym, bars, json_mode=True)
    except Exception:
        return None


def audit(use_ibkr: bool = False) -> dict:
    universe, source = load_trading_universe()
    rows: list[dict] = []
    ib = None
    if use_ibkr:
        try:
            from ib_insync import IB, Stock  # noqa: F401
            ib = IB()
            ib.connect("127.0.0.1", 4002, clientId=98, timeout=10)
        except Exception as e:
            print(f"[WARN] IBKR 연결 실패 — IBKR 피드 제외: {e}", file=sys.stderr)
            ib = None

    for u in universe:
        sym = u["symbol"]
        region = u.get("region", "US")
        currency = u.get("currency", "USD")

        # Alpaca는 미국 주식만 지원 → 비교는 US 종목에 한해 Alpaca 포함
        alp = _alpaca_signal(sym) if region.upper() == "US" else None
        yah = _yahoo_signal(sym, region)

        ibk = None
        if ib is not None:
            try:
                from ib_insync import Stock
                c = Stock(sym, u.get("exchange", "SMART"), currency)
                ib.qualifyContracts(c)
                ibk = calc_full_signal(ib, c, json_mode=True)
            except Exception:
                ibk = None

        def g(d: dict | None, k: str):
            return d.get(k) if isinstance(d, dict) and d.get(k) not in (0, None) else None

        # 기준 피드: Alpaca(US) 우선, 아니면 Yahoo
        base = alp if (alp and region.upper() == "US") else yah
        base_name = "alpaca" if base is alp and alp else "yahoo"

        entry = {
            "symbol": sym,
            "region": region,
            "currency": currency,
            "base_feed": base_name,
            "alpaca": {k: g(alp, k) for k in ("current_price", "atr", "s1_high", "s2_high", "signal")} if alp else None,
            "yahoo": {k: g(yah, k) for k in ("current_price", "atr", "s1_high", "s2_high", "signal")} if yah else None,
            "ibkr": {k: g(ibk, k) for k in ("current_price", "atr", "s1_high", "s2_high", "signal")} if ibk else None,
        }

        # 편차: 기준(base) 대비 다른 피드들
        drifts = {}
        flags = []
        for name, feed in (("alpaca", alp), ("yahoo", yah), ("ibkr", ibk)):
            if feed is None or feed is base:
                continue
            d_price = _pct_delta(g(base, "current_price"), g(feed, "current_price"))
            d_atr = _pct_delta(g(base, "atr"), g(feed, "atr"))
            d_s2 = _pct_delta(g(base, "s2_high"), g(feed, "s2_high"))
            drifts[f"{base_name}_vs_{name}"] = {"price_pct": d_price, "atr_pct": d_atr, "s2_high_pct": d_s2}
            if d_price is not None and d_price > PRICE_DRIFT_WARN_PCT:
                flags.append(f"⚠️ price drift {base_name}↔{name} {d_price}%")
            if d_atr is not None and d_atr > ATR_DRIFT_WARN_PCT:
                flags.append(f"⚠️ ATR drift {base_name}↔{name} {d_atr}%")
            # 돌파 신호 불일치(둘 다 유효 신호일 때)
            bs, fs = g(base, "signal"), g(feed, "signal")
            if bs and fs and bs != fs and "breakout" in f"{bs}{fs}":
                flags.append(f"🚨 signal mismatch {base_name}={bs} {name}={fs}")

        entry["drifts"] = drifts
        entry["flags"] = flags
        rows.append(entry)

    if ib is not None:
        try:
            ib.disconnect()
        except Exception:
            pass

    # 요약
    all_atr = [d["atr_pct"] for r in rows for d in r["drifts"].values() if d.get("atr_pct") is not None]
    all_price = [d["price_pct"] for r in rows for d in r["drifts"].values() if d.get("price_pct") is not None]
    flagged = [r["symbol"] for r in rows if r["flags"]]
    summary = {
        "universe_source": source,
        "symbols_audited": len(rows),
        "ibkr_included": ib is not None,
        "max_atr_drift_pct": max(all_atr) if all_atr else None,
        "avg_atr_drift_pct": round(sum(all_atr) / len(all_atr), 3) if all_atr else None,
        "max_price_drift_pct": max(all_price) if all_price else None,
        "flagged_symbols": flagged,
        "atr_drift_warn_pct": ATR_DRIFT_WARN_PCT,
    }
    return {"summary": summary, "rows": rows}


def _fmt(v) -> str:
    return f"{v:.2f}" if isinstance(v, (int, float)) else "—"


def print_report(result: dict) -> None:
    s = result["summary"]
    print("=" * 70)
    print("가격 피드 정밀도 오디트 — Alpaca vs Yahoo" + (" vs IBKR" if s["ibkr_included"] else ""))
    print(f"유니버스: {s['universe_source']} | 종목: {s['symbols_audited']} | ATR 경고 임계: {s['atr_drift_warn_pct']}%")
    print("=" * 70)
    for r in result["rows"]:
        a, y = r.get("alpaca"), r.get("yahoo")
        line = f"  {r['symbol']:<8}({r['region']}) "
        if a:
            line += f"Alpaca[p={_fmt(a.get('current_price'))} atr={_fmt(a.get('atr'))} S2={_fmt(a.get('s2_high'))} {a.get('signal') or '-'}] "
        if y:
            line += f"Yahoo[p={_fmt(y.get('current_price'))} atr={_fmt(y.get('atr'))} S2={_fmt(y.get('s2_high'))} {y.get('signal') or '-'}]"
        print(line)
        for f in r["flags"]:
            print(f"      {f}")
    print("-" * 70)
    print(f"최대 ATR 편차: {_fmt(s['max_atr_drift_pct'])}% | 평균 ATR 편차: {_fmt(s['avg_atr_drift_pct'])}% | "
          f"최대 가격 편차: {_fmt(s['max_price_drift_pct'])}%")
    if s["flagged_symbols"]:
        print(f"⚠️ 편차/불일치 종목: {', '.join(s['flagged_symbols'])}")
    else:
        print("✅ 임계 초과 편차 없음")


def main() -> int:
    parser = argparse.ArgumentParser(description="가격 피드 정밀도 오디트")
    parser.add_argument("--json", action="store_true", help="JSON 한 줄 출력")
    parser.add_argument("--ibkr", action="store_true", help="IBKR 라이브 피드 포함(게이트웨이 필요)")
    args = parser.parse_args()
    result = audit(use_ibkr=args.ibkr)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print_report(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
