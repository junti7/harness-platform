"""Turtle 백테스트 — 수정 시스템(P0/P1) vs 기존 버그 시스템 vs Buy&Hold.

목적(2026-06-27 CEO): P0/P1 수정 후 시스템에 '엣지'가 있는지, 아니면 본전 횡보인지 수치로 확인.

데이터: Alpaca IEX 일봉(~2020-07~). SIP 미허용(무료 티어). IEX는 체결 일부만 반영하므로 가격이
SIP와 미세 차이 — 일봉 돌파 시스템 방향성 검증엔 충분(절대수익보다 상대비교가 목적).

모델 단순화(명시):
  - 일봉 종가 기준 신호(장중 돌파 미모델). 진입=돌파일 종가, 청산=청산일 종가.
  - 손절=저가가 stop 이탈 시 stop 가격 체결(갭다운이면 시가 체결). 슬리피지/수수료 0(paper).
  - 1유닛(피라미딩 없음 — 현재 시스템 그대로).

전략 파라미터:
  진입 S1=20일 / S2=55일 고가 돌파(롱). 청산 S1=10일 / S2=20일 저가. ATR=20. 손절=2N.
  수정(P1): 사이징=(equity×1%)/(2N), 추세필터=100일 SMA 위에서만 롱, 상관한도(동등ETF·그룹).
  기존(버그): 사이징=(equity×1%)/(1N), 추세필터 없음, 상관한도 없음.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

from scripts.alpaca_paper_trading import _data_get

UNIVERSE = ["NVDA", "SMH", "SOXX", "BOTZ", "TSLA", "PLTR", "ROBO", "QQQ"]
START = "2020-07-01"
END = "2026-06-26"
INITIAL = 100_000.0

# 상관 한도(P1과 동일)
EQUIVALENT_SETS = [frozenset({"SMH", "SOXX"}), frozenset({"BOTZ", "ROBO"})]
CORR_GROUP = {"SMH": "SEMI", "SOXX": "SEMI", "NVDA": "SEMI", "QQQ": "SEMI",
              "BOTZ": "ROBOT", "ROBO": "ROBOT", "TSLA": "AUTO", "PLTR": "SW"}
MAX_CORR_UNITS = 3
MAX_POSITIONS = 6
RISK_PCT = 0.01
ATR_PERIOD = 20
STOP_MULT = 2
TREND_MA = 100


def fetch(sym: str) -> list[dict]:
    d = _data_get(f"/stocks/{sym}/bars", params={
        "timeframe": "1Day", "start": START, "end": END,
        "limit": 10000, "adjustment": "all", "feed": "iex"})
    return sorted(d.get("bars") or [], key=lambda b: b.get("t", ""))


def atr(bars, i, period=ATR_PERIOD):
    if i < period:
        return 0.0
    trs = []
    for j in range(i - period + 1, i + 1):
        h, lo, pc = bars[j]["h"], bars[j]["l"], bars[j - 1]["c"]
        trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
    return sum(trs) / period


_BAR_CACHE: dict = {}


def run_backtest(corrected: bool, size_div: float | None = None, label: str | None = None) -> dict:
    # size_div: 사이징 분모 배수(2.0=2N 진짜1%, 1.0=1N 클래식2%). None이면 corrected→2N, else 1N.
    if size_div is None:
        size_div = STOP_MULT if corrected else 1.0
    data = _BAR_CACHE or {s: fetch(s) for s in UNIVERSE}
    _BAR_CACHE.update(data)
    # 날짜→{sym: bar} 인덱스
    idx = {s: {b["t"][:10]: k for k, b in enumerate(bars)} for s, bars in data.items()}
    all_dates = sorted({b["t"][:10] for bars in data.values() for b in bars})

    cash = INITIAL
    pos = {}  # sym -> {qty, entry, stop, system}
    trades = []
    equity_curve = []

    def held_syms():
        return set(pos.keys())

    def corr_blocked(sym):
        if not corrected:
            return False
        held = held_syms()
        for eq in EQUIVALENT_SETS:
            if sym in eq and (held & (eq - {sym})):
                return True
        grp = CORR_GROUP.get(sym)
        if grp and sum(1 for h in held if CORR_GROUP.get(h) == grp) >= MAX_CORR_UNITS:
            return True
        return False

    for date in all_dates:
        # mark-to-market & 청산 먼저
        for sym in list(pos.keys()):
            if date not in idx[sym]:
                continue
            i = idx[sym][date]
            bars = data[sym]
            p = pos[sym]
            exit_days = 10 if p["system"] == "S1" else 20
            day = bars[i]
            # 손절(저가 이탈) — gap 이면 시가 체결
            if day["l"] <= p["stop"]:
                fill = min(day["o"], p["stop"]) if day["o"] < p["stop"] else p["stop"]
                cash += p["qty"] * fill
                trades.append((sym, p["entry"], fill, p["qty"], "stop"))
                del pos[sym]
                continue
            # N일 저가 청산
            if i >= exit_days:
                exit_low = min(b["l"] for b in bars[i - exit_days:i])
                if day["c"] < exit_low:
                    cash += p["qty"] * day["c"]
                    trades.append((sym, p["entry"], day["c"], p["qty"], "exit"))
                    del pos[sym]

        # 진입 스캔
        equity = cash + sum(pos[s]["qty"] * data[s][idx[s][date]]["c"]
                            for s in pos if date in idx[s])
        for sym in UNIVERSE:
            if sym in pos or date not in idx[sym]:
                continue
            if len(pos) >= MAX_POSITIONS:
                break
            i = idx[sym][date]
            bars = data[sym]
            if i < 56:
                continue
            cp = bars[i]["c"]
            s1_high = max(b["h"] for b in bars[i - 20:i])
            s2_high = max(b["h"] for b in bars[i - 55:i])
            system = None
            if cp > s2_high:
                system = "S2"
            elif cp > s1_high:
                system = "S1"
            if not system:
                continue
            a = atr(bars, i)
            if a <= 0:
                continue
            if corr_blocked(sym):
                continue
            if corrected:
                sma = sum(b["c"] for b in bars[i - TREND_MA + 1:i + 1]) / TREND_MA if i >= TREND_MA else None
                if sma is not None and cp <= sma:
                    continue
                denom = size_div * a
            else:
                denom = size_div * a
            qty = int((equity * RISK_PCT) / denom)
            if qty <= 0 or qty * cp > cash:
                continue
            cash -= qty * cp
            pos[sym] = {"qty": qty, "entry": cp, "stop": cp - STOP_MULT * a, "system": system}

        equity = cash + sum(pos[s]["qty"] * data[s][idx[s][date]]["c"]
                            for s in pos if date in idx[s])
        equity_curve.append((date, equity))

    res = summarize(corrected, trades, equity_curve)
    if label:
        res["system"] = label
    return res


def summarize(corrected, trades, curve):
    final = curve[-1][1]
    ret = (final / INITIAL - 1) * 100
    peak = -1e9
    mdd = 0
    for _, e in curve:
        peak = max(peak, e)
        mdd = min(mdd, (e / peak - 1) * 100)
    wins = [(b, a) for _, b, a, q, _ in [(t[0], t[1], t[2], t[3], t[4]) for t in trades] if a > b]
    pnls = [(a - b) * q for _, b, a, q, _ in trades]
    win_pnls = [p for p in pnls if p > 0]
    loss_pnls = [p for p in pnls if p <= 0]
    n = len(trades)
    win_rate = len(win_pnls) / n * 100 if n else 0
    pf = (sum(win_pnls) / -sum(loss_pnls)) if loss_pnls and sum(loss_pnls) != 0 else float("inf")
    yrs = len(curve) / 252
    cagr = ((final / INITIAL) ** (1 / yrs) - 1) * 100 if yrs > 0 else 0
    return {
        "system": "수정(P0/P1)" if corrected else "기존(버그)",
        "final": final, "return_pct": ret, "cagr": cagr, "mdd": mdd,
        "trades": n, "win_rate": win_rate, "profit_factor": pf,
        "avg_win": (sum(win_pnls) / len(win_pnls)) if win_pnls else 0,
        "avg_loss": (sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0,
        "curve": curve,
    }


def buy_hold(sym="SMH"):
    bars = fetch(sym)
    first, last = bars[0]["c"], bars[-1]["c"]
    ret = (last / first - 1) * 100
    peak = -1e9
    mdd = 0
    for b in bars:
        peak = max(peak, b["c"])
        mdd = min(mdd, (b["c"] / peak - 1) * 100)
    yrs = len(bars) / 252
    cagr = ((last / first) ** (1 / yrs) - 1) * 100 if yrs > 0 else 0
    return {"system": f"B&H {sym}", "return_pct": ret, "cagr": cagr, "mdd": mdd}


def main():
    print(f"백테스트 {START} ~ {END} | 유니버스 {UNIVERSE} | 초기 ${INITIAL:,.0f}\n")
    rows = [
        run_backtest(corrected=False, size_div=1.0, label="기존버그(필터X·1N)"),
        run_backtest(corrected=True, size_div=2.0, label="수정 2N(진짜1%)"),
        run_backtest(corrected=True, size_div=1.5, label="수정 1.5N(~1.3%)"),
        run_backtest(corrected=True, size_div=1.0, label="수정 1N(클래식2%)"),
    ]
    bh = buy_hold("SMH")
    bhq = buy_hold("QQQ")

    print(f"{'시스템':16} {'최종수익%':>10} {'CAGR%':>8} {'MaxDD%':>8} {'거래수':>6} {'승률%':>7} {'PF':>6} {'평균익':>9} {'평균손':>9}")
    print("-" * 92)
    for r in rows:
        print(f"{r['system']:16} {r['return_pct']:>10.1f} {r['cagr']:>8.1f} {r['mdd']:>8.1f} "
              f"{r['trades']:>6} {r['win_rate']:>7.1f} {r['profit_factor']:>6.2f} "
              f"{r['avg_win']:>9.0f} {r['avg_loss']:>9.0f}")
    for r in (bh, bhq):
        print(f"{r['system']:16} {r['return_pct']:>10.1f} {r['cagr']:>8.1f} {r['mdd']:>8.1f} "
              f"{'—':>6} {'—':>7} {'—':>6} {'—':>9} {'—':>9}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
