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


def _hybrid_risk_frac(system, cp, ma100, ma200, atr_now, atr_prev) -> float:
    """국면 적응형 risk 예산(손절=2N까지 손실 비중). 강추세·저변동=↑, 횡보·고변동=↓.
    base 1% → S2(강돌파)·200일선 위·변동축소면 최대 2%, 약하거나 변동확대면 0.5%까지."""
    f = 0.01
    if system == "S2":
        f *= 1.4                      # 55일 돌파 = 강한 추세
    if ma200 and cp > ma200:
        f *= 1.3                      # 장기 상승추세
    elif ma100 and cp > ma100:
        f *= 1.0
    if atr_prev and atr_now:
        vr = atr_now / atr_prev
        if vr > 1.3:
            f *= 0.6                   # 변동성 확대 → 축소
        elif vr < 0.9:
            f *= 1.15                  # 변동성 수축 → 확대
    return max(0.005, min(0.02, f))


def run_backtest(corrected: bool, size_div: float | None = None, label: str | None = None,
                 hybrid: bool = False, heat_cap: float | None = None,
                 market_regime: bool = False) -> dict:
    # size_div: 사이징 분모 배수(2.0=2N 진짜1%, 1.0=1N 클래식2%). None이면 corrected→2N, else 1N.
    # hybrid=True 면 _hybrid_risk_frac 로 국면별 risk 예산. heat_cap: 포트폴리오 합산 risk 상한.
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
    # 시장 레짐 필터: 광범위 반도체지수(SMH) 200일선. 위=risk-on, 아래=risk-off(베어).
    smh = data.get("SMH", [])
    smh_idx = {b["t"][:10]: k for k, b in enumerate(smh)}

    def market_risk_on(date):
        if date not in smh_idx:
            return True
        k = smh_idx[date]
        if k < 200:
            return True
        ma = sum(b["c"] for b in smh[k - 199:k + 1]) / 200
        return smh[k]["c"] > ma

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
            ma100 = sum(b["c"] for b in bars[i - 100 + 1:i + 1]) / 100 if i >= 100 else None
            ma200 = sum(b["c"] for b in bars[i - 200 + 1:i + 1]) / 200 if i >= 200 else None
            if corrected:
                if ma100 is not None and cp <= ma100:
                    continue
            if market_regime:
                # 불장(SMH>200MA): 공격 1N(2%). 베어: 방어 0.5% + 약한 S1 진입 차단(S2만).
                risk_on = market_risk_on(date)
                if not risk_on and system == "S1":
                    continue
                f = 0.02 if risk_on else 0.005
                qty = int((equity * f) / (STOP_MULT * a))
            elif hybrid:
                atr_prev = atr(bars, i - 60) if i >= 60 + ATR_PERIOD else a
                f = _hybrid_risk_frac(system, cp, ma100, ma200, a, atr_prev)
                qty = int((equity * f) / (STOP_MULT * a))   # risk-to-stop(2N) = f
            else:
                qty = int((equity * RISK_PCT) / (size_div * a))
            if qty <= 0 or qty * cp > cash:
                continue
            new_risk = qty * STOP_MULT * a
            if heat_cap is not None:
                open_risk = sum(p["risk"] for p in pos.values())
                if open_risk + new_risk > heat_cap * equity:
                    continue
            cash -= qty * cp
            pos[sym] = {"qty": qty, "entry": cp, "stop": cp - STOP_MULT * a,
                        "system": system, "risk": new_risk}

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
        "mar": (cagr / abs(mdd)) if mdd else 0,
        "trades": n, "win_rate": win_rate, "profit_factor": pf,
        "avg_win": (sum(win_pnls) / len(win_pnls)) if win_pnls else 0,
        "avg_loss": (sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0,
        "curve": curve,
    }


def run_ls(pyramid: bool = False, allow_short: bool = True, label: str = "") -> dict:
    """롱+숏(+선택 피라미딩) 1N 사이징 백테스트. #2 검증용.

    회계: equity = cash_base(실현) + Σ미실현. 진입 시 cash 불변(미실현으로 추적), 청산 시 실현 반영.
    gross 노출 ≤ equity(무레버리지). 피라미딩: ½N 유리 이동마다 유닛 추가(최대 4), stop 상향.
    """
    data = _BAR_CACHE or {s: fetch(s) for s in UNIVERSE}
    _BAR_CACHE.update(data)
    idx = {s: {b["t"][:10]: k for k, b in enumerate(bars)} for s, bars in data.items()}
    all_dates = sorted({b["t"][:10] for bars in data.values() for b in bars})
    MAX_UNITS = 4

    cashb = [INITIAL]  # 실현 자본(리스트=클로저 가변)
    pos = {}  # sym -> {dir, N, stop, system, units:[{qty,entry}], last_entry}
    trades = []
    curve = []

    def unreal():
        u = 0.0
        for s, p in pos.items():
            if all_dates_cur not in idx[s]:
                continue
            cur = data[s][idx[s][all_dates_cur]]["c"]
            for un in p["units"]:
                u += un["qty"] * ((cur - un["entry"]) if p["dir"] == "long" else (un["entry"] - cur))
        return u

    def gross():
        g = 0.0
        for s, p in pos.items():
            cur = data[s][idx[s][all_dates_cur]]["c"] if all_dates_cur in idx[s] else p["units"][0]["entry"]
            g += sum(un["qty"] for un in p["units"]) * cur
        return g

    def corr_blocked(sym):
        held = set(pos.keys())
        for eq in EQUIVALENT_SETS:
            if sym in eq and (held & (eq - {sym})):
                return True
        grp = CORR_GROUP.get(sym)
        if grp and sum(1 for h in held if CORR_GROUP.get(h) == grp) >= MAX_CORR_UNITS:
            return True
        return False

    for all_dates_cur in all_dates:
        date = all_dates_cur
        # 1) 청산/손절/피라미딩
        for sym in list(pos.keys()):
            if date not in idx[sym]:
                continue
            i = idx[sym][date]
            bars = data[sym]
            p = pos[sym]
            day = bars[i]
            exit_days = 10 if p["system"] == "S1" else 20
            closed = False
            if p["dir"] == "long":
                if day["l"] <= p["stop"]:
                    px = min(day["o"], p["stop"]) if day["o"] < p["stop"] else p["stop"]
                    closed, reason = True, "stop"
                elif i >= exit_days and day["c"] < min(b["l"] for b in bars[i - exit_days:i]):
                    px, closed, reason = day["c"], True, "exit"
            else:  # short
                if day["h"] >= p["stop"]:
                    px = max(day["o"], p["stop"]) if day["o"] > p["stop"] else p["stop"]
                    closed, reason = True, "stop"
                elif i >= exit_days and day["c"] > max(b["h"] for b in bars[i - exit_days:i]):
                    px, closed, reason = day["c"], True, "exit"
            if closed:
                realized = sum(un["qty"] * ((px - un["entry"]) if p["dir"] == "long" else (un["entry"] - px))
                               for un in p["units"])
                cashb[0] += realized
                trades.append((sym, p["dir"], realized, reason, len(p["units"])))
                del pos[sym]
                continue
            # 피라미딩: ½N 유리 이동 시 유닛 추가
            if pyramid and len(p["units"]) < MAX_UNITS:
                N = p["N"]
                cp = day["c"]
                trig = p["last_entry"] + 0.5 * N if p["dir"] == "long" else p["last_entry"] - 0.5 * N
                add = (cp >= trig) if p["dir"] == "long" else (cp <= trig)
                if add:
                    eq = cashb[0] + unreal()
                    qty = int((eq * RISK_PCT) / N)
                    if qty > 0 and gross() + qty * cp <= eq:
                        p["units"].append({"qty": qty, "entry": cp})
                        p["last_entry"] = cp
                        p["stop"] = (cp - STOP_MULT * N) if p["dir"] == "long" else (cp + STOP_MULT * N)

        # 2) 신규 진입
        equity = cashb[0] + unreal()
        for sym in UNIVERSE:
            if sym in pos or date not in idx[sym] or len(pos) >= MAX_POSITIONS:
                continue
            i = idx[sym][date]
            bars = data[sym]
            if i < 56:
                continue
            cp = bars[i]["c"]
            a = atr(bars, i)
            if a <= 0 or corr_blocked(sym):
                continue
            ma100 = sum(b["c"] for b in bars[i - 99:i + 1]) / 100 if i >= 99 else None
            s1h = max(b["h"] for b in bars[i - 20:i]); s2h = max(b["h"] for b in bars[i - 55:i])
            s1l = min(b["l"] for b in bars[i - 20:i]); s2l = min(b["l"] for b in bars[i - 55:i])
            direction = system = None
            if cp > s2h:
                direction, system = "long", "S2"
            elif cp > s1h:
                direction, system = "long", "S1"
            elif allow_short and cp < s2l:
                direction, system = "short", "S2"
            elif allow_short and cp < s1l:
                direction, system = "short", "S1"
            if not direction:
                continue
            if ma100 is not None:
                if direction == "long" and cp <= ma100:
                    continue
                if direction == "short" and cp >= ma100:
                    continue
            qty = int((equity * RISK_PCT) / a)
            if qty <= 0 or gross() + qty * cp > equity:
                continue
            stop = (cp - STOP_MULT * a) if direction == "long" else (cp + STOP_MULT * a)
            pos[sym] = {"dir": direction, "N": a, "stop": stop, "system": system,
                        "units": [{"qty": qty, "entry": cp}], "last_entry": cp}

        curve.append((date, cashb[0] + unreal()))

    # summarize (curve 기반)
    final = curve[-1][1]
    ret = (final / INITIAL - 1) * 100
    peak = -1e9; mdd = 0
    for _, e in curve:
        peak = max(peak, e); mdd = min(mdd, (e / peak - 1) * 100)
    pnls = [t[2] for t in trades]
    wins = [p for p in pnls if p > 0]; losses = [p for p in pnls if p <= 0]
    n = len(trades)
    pf = (sum(wins) / -sum(losses)) if losses and sum(losses) != 0 else float("inf")
    yrs = len(curve) / 252
    cagr = ((final / INITIAL) ** (1 / yrs) - 1) * 100 if yrs > 0 and final > 0 else -100
    return {"system": label, "return_pct": ret, "cagr": cagr, "mdd": mdd,
            "mar": (cagr / abs(mdd)) if mdd else 0, "trades": n,
            "win_rate": (len(wins) / n * 100) if n else 0, "profit_factor": pf,
            "avg_win": 0, "avg_loss": 0, "curve": curve}



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
        run_backtest(corrected=True, size_div=2.0, label="수정 2N(진짜1%)"),
        run_backtest(corrected=True, size_div=1.0, label="수정 1N(클래식2%)"),
        run_ls(allow_short=False, pyramid=False, label="롱전용 1N(재확인)"),
        run_ls(allow_short=True, pyramid=False, label="롱+숏 1N"),
        run_ls(allow_short=True, pyramid=True, label="롱+숏+피라미딩 1N"),
        run_ls(allow_short=False, pyramid=True, label="롱전용+피라미딩 1N"),
    ]
    bh = buy_hold("SMH")
    bhq = buy_hold("QQQ")

    print(f"{'시스템':18} {'최종%':>8} {'CAGR%':>7} {'MaxDD%':>8} {'MAR':>5} {'거래':>5} {'승률%':>6} {'PF':>5}")
    print("-" * 70)
    for r in rows:
        print(f"{r['system']:18} {r['return_pct']:>8.1f} {r['cagr']:>7.1f} {r['mdd']:>8.1f} "
              f"{r['mar']:>5.2f} {r['trades']:>5} {r['win_rate']:>6.1f} {r['profit_factor']:>5.2f}")
    for r in (bh, bhq):
        mar = r['cagr'] / abs(r['mdd']) if r['mdd'] else 0
        print(f"{r['system']:18} {r['return_pct']:>8.1f} {r['cagr']:>7.1f} {r['mdd']:>8.1f} "
              f"{mar:>5.2f} {'—':>5} {'—':>6} {'—':>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
