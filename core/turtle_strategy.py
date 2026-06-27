"""Turtle 전략 코어 — **브로커 중립**(Alpaca/IBKR 공용). 페이즈 B 일원화(2026-06-27).

여기에는 *순수 결정 로직*만 둔다(주문/계좌/시세 호출 없음). 브로커별 어댑터
(scripts/turtle_auto_trader.py=Alpaca, scripts/ibkr_tws_paper_trader.py=IBKR)가 데이터(시세·계좌·
포지션)를 가져와 이 함수들에 넘기고, 반환된 '의도'를 각자 브로커 API로 실행한다.

이렇게 하면 검증된 전략(사이징·게이트·상관한도·추세필터·청산·피라미딩)이 단일 출처가 되어
페이퍼(Alpaca)와 실거래(IBKR)가 동일 로직으로 돌고, 두 코드베이스 드리프트(F5 사고)를 막는다.
"""
from __future__ import annotations

import os

# ── 파라미터 (단일 출처) ──────────────────────────────────────────────────────
TURTLE_S1_ENTRY = 20
TURTLE_S2_ENTRY = 55
TURTLE_ATR_PERIOD = 20
TURTLE_STOP_MULT = 2
TURTLE_RISK_PCT = 0.01                                              # 1N 사이징(클래식 1유닛)
TURTLE_MAX_RISK_PCT = float(os.getenv("PAPER_MAX_TRADE_RISK_PCT", "0.02"))   # 단일 트레이드 ≤2%
MAX_PORTFOLIO_HEAT = float(os.getenv("PAPER_MAX_PORTFOLIO_HEAT", "0.10"))    # 포트폴리오 heat 상한
MAX_UNITS_PER_GROUP = int(os.getenv("PAPER_MAX_CORR_UNITS", "3"))            # 상관 그룹 유닛 상한

# 추세필터
TREND_FILTER_ENABLED = os.getenv("PAPER_TREND_FILTER", "true").lower() == "true"
TREND_MA_DAYS = int(os.getenv("PAPER_TREND_MA_DAYS", "100"))

# 피라미딩 (롱 전용)
PYRAMID_ENABLED = os.getenv("PAPER_PYRAMID_ENABLED", "true").lower() == "true"
MAX_UNITS = int(os.getenv("PAPER_MAX_UNITS", "4"))
PYRAMID_STEP_N = float(os.getenv("PAPER_PYRAMID_STEP_N", "0.5"))

# 무상관 분산 sleeve
DIVERSIFIERS = ["TLT", "GLD", "DBC", "UUP"]

# 상관 그룹(측정상관 기준). 동등 ETF 동시보유 금지 + 그룹별 유닛 상한.
EQUIVALENT_ETF_SETS = [frozenset({"SMH", "SOXX"}), frozenset({"BOTZ", "ROBO"})]
CORR_GROUP = {
    "SMH": "SEMI", "SOXX": "SEMI", "NVDA": "SEMI", "TSM": "SEMI", "MU": "SEMI",
    "AVGO": "SEMI", "ASX": "SEMI", "QQQ": "SEMI", "ROBO": "SEMI", "BOTZ": "SEMI",
    "COHR": "SEMI",
    "SYM": "ROBOT",
    "TSLA": "AUTO",
    "GOOG": "AIPLATFORM", "META": "AIPLATFORM",
    "PLTR": "AISW", "SNOW": "AISW", "CRWD": "AISW", "DDOG": "AISW",
    "VRT": "POWER", "CEG": "POWER", "VST": "POWER", "GEV": "POWER", "PWR": "POWER",
    "TLT": "BOND", "GLD": "GOLD", "DBC": "COMMOD", "UUP": "USD",
}


# ── 순수 지표/신호 ────────────────────────────────────────────────────────────

def compute_atr(bars: list[dict], period: int = TURTLE_ATR_PERIOD) -> float:
    """Average True Range. bars=[{o,h,l,c,t}] 시간순. 데이터 부족 시 0."""
    if len(bars) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(bars)):
        h = float(bars[i].get("h", 0))
        lo = float(bars[i].get("l", 0))
        pc = float(bars[i - 1].get("c", 0))
        trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
    if len(trs) < period:
        return 0.0
    return round(sum(trs[-period:]) / period, 4)


def signal_from_bars(symbol: str, bars: list[dict]) -> dict:
    """Donchian 돌파 신호(브로커 무관, bars만 입력). Alpaca get_turtle_signal과 동일 로직."""
    if len(bars) < TURTLE_S2_ENTRY + 2:
        return {"symbol": symbol, "signal": "insufficient_data", "system": None,
                "direction": None, "current_price": 0, "atr": 0}
    cp = float(bars[-1].get("c", 0))
    atr = compute_atr(bars, TURTLE_ATR_PERIOD)
    s1h = max(float(b.get("h", 0)) for b in bars[-TURTLE_S1_ENTRY - 1:-1])
    s1l = min(float(b.get("l", 0)) for b in bars[-TURTLE_S1_ENTRY - 1:-1])
    s2h = max(float(b.get("h", 0)) for b in bars[-TURTLE_S2_ENTRY - 1:-1])
    s2l = min(float(b.get("l", 0)) for b in bars[-TURTLE_S2_ENTRY - 1:-1])
    signal, system, direction = "neutral", None, None
    if cp > s2h:
        signal, system, direction = "breakout_long", "S2", "long"
    elif cp < s2l:
        signal, system, direction = "breakout_short", "S2", "short"
    elif cp > s1h:
        signal, system, direction = "breakout_long", "S1", "long"
    elif cp < s1l:
        signal, system, direction = "breakout_short", "S1", "short"
    return {"symbol": symbol, "signal": signal, "direction": direction, "system": system,
            "current_price": round(cp, 2), "atr": round(atr, 4),
            "s1_high": round(s1h, 2), "s1_low": round(s1l, 2),
            "s2_high": round(s2h, 2), "s2_low": round(s2l, 2),
            "stop_long": round(cp - TURTLE_STOP_MULT * atr, 2) if atr > 0 else None,
            "stop_short": round(cp + TURTLE_STOP_MULT * atr, 2) if atr > 0 else None}


# ── 순수 사이징/게이트 ────────────────────────────────────────────────────────

def size_shares(account_value: float, atr: float) -> int:
    """1N 사이징(클래식 Turtle 1유닛). 손절 2N → 실효 리스크 ~2%."""
    if atr <= 0 or account_value <= 0:
        return 0
    return int((account_value * TURTLE_RISK_PCT) / atr)


def turtle_gate_check(signal: dict, account_value: float, max_risk_pct: float | None = None) -> dict:
    """진입 5항목 게이트 + 1N 사이징. 리스크는 2N(손절거리) 기준으로 측정해 ≤2% 강제.
    max_risk_pct 미지정 시 모듈 기본(어댑터가 자기 config를 주입할 수 있게 파라미터화)."""
    if max_risk_pct is None:
        max_risk_pct = TURTLE_MAX_RISK_PCT
    checks = {}
    cp = signal["current_price"]
    atr = signal["atr"]
    checks["signal"] = signal["signal"] == "breakout_long"
    checks["atr"] = atr > 0
    if atr > 0:
        shares = size_shares(account_value, atr)
        stop_distance = TURTLE_STOP_MULT * atr
        risk_pct = (shares * stop_distance) / account_value if account_value else 0
        checks["risk_pct"] = risk_pct <= max_risk_pct * 1.05
    else:
        stop_distance = 0
        shares = 0
        checks["risk_pct"] = False
    stop_loss = round(cp - TURTLE_STOP_MULT * atr, 2)
    checks["stop_loss"] = stop_loss > 0
    checks["exit_system"] = signal.get("system") in ("S1", "S2")
    return {
        "symbol": signal["symbol"], "passed": all(checks.values()), "checks": checks,
        "shares": shares, "stop_loss": stop_loss, "position_value": round(shares * cp, 2),
        "risk_dollars": round(shares * stop_distance, 2),
        "risk_pct": round((shares * stop_distance) / account_value * 100, 3) if account_value else 0,
        "system": signal.get("system"), "direction": signal.get("direction"),
    }


# ── 순수 상관 한도 / heat ─────────────────────────────────────────────────────

def correlation_block(symbol: str, held: set, corr_group: dict | None = None,
                      equivalent_sets: list | None = None, max_units: int | None = None) -> tuple[bool, str]:
    """동등 ETF 동시보유 금지 + 상관 그룹 유닛 상한. 막으면 (True, 사유).
    config 미지정 시 모듈 기본(어댑터가 자기 config 주입 가능)."""
    cg = corr_group if corr_group is not None else CORR_GROUP
    eqsets = equivalent_sets if equivalent_sets is not None else EQUIVALENT_ETF_SETS
    cap = max_units if max_units is not None else MAX_UNITS_PER_GROUP
    su = symbol.upper()
    for eq in eqsets:
        if su in eq and (held & (eq - {su})):
            twin = ", ".join(sorted(eq - {su}))
            return True, f"equivalent_etf_held ({twin})"
    grp = cg.get(su)
    if grp:
        same = sum(1 for h in held if cg.get(h.upper()) == grp)
        if same >= cap:
            return True, f"corr_group_full ({grp}={same}/{cap})"
    return False, ""


def portfolio_heat(positions: dict, account_value: float) -> float:
    """보유 포지션 합산 risk ÷ 계좌. risk_usd(피라미딩 정확치) 우선, 없으면 qty×|entry−stop|."""
    if not account_value:
        return 0.0
    tot = 0.0
    for p in positions.values():
        if p.get("risk_usd") is not None:
            tot += p["risk_usd"]
            continue
        q = p.get("qty", 0) or 0
        e = p.get("entry_price") or 0
        s = p.get("stop_loss") or 0
        if e and s:
            tot += q * abs(e - s)
    return tot / account_value


# ── 순수 추세필터 / 청산 / 피라미딩 결정 ──────────────────────────────────────

def trend_filter_ok(closes: list[float], current_price: float,
                    ma_days: int = TREND_MA_DAYS, enabled: bool = TREND_FILTER_ENABLED) -> tuple[bool, str]:
    """장기 MA 위에서만 롱 허용. 데이터 부족 시 fail-open."""
    if not enabled:
        return True, "filter_off"
    if len(closes) < ma_days:
        return True, f"insufficient_bars_failopen({len(closes)}<{ma_days})"
    ma = sum(closes[-ma_days:]) / ma_days
    if current_price > ma:
        return True, f"above_ma{ma_days}(${current_price:.2f}>${ma:.2f})"
    return False, f"below_ma{ma_days}(${current_price:.2f}<=${ma:.2f})"


def exit_signal(bars: list[dict], system: str, side: str = "long") -> tuple[bool, str]:
    """Turtle 청산: 롱=N일 저가 이탈, 숏=N일 고가 이탈. (S1:10, S2:20)."""
    exit_days = 10 if system == "S1" else 20
    if len(bars) < exit_days + 1:
        return False, "insufficient_bars"
    cur = float(bars[-1].get("c", 0))
    window = bars[-exit_days - 1:-1]
    if side == "long":
        exit_low = min(float(b.get("l", 0)) for b in window)
        if cur < exit_low:
            return True, f"price_below_{exit_days}d_low (${cur:.2f} < ${exit_low:.2f})"
    else:
        exit_high = max(float(b.get("h", 0)) for b in window)
        if cur > exit_high:
            return True, f"price_above_{exit_days}d_high (${cur:.2f} > ${exit_high:.2f})"
    return False, "hold"


def pyramid_decision(tracked: dict, current_price: float, account_value: float,
                     enabled: bool | None = None, max_units: int | None = None,
                     step_n: float | None = None) -> dict | None:
    """롱 피라미딩 결정(순수). 추가 조건 충족 시 {qty_add,new_stop,new_total,new_risk,unit}, 아니면 None.
    config 미지정 시 모듈 기본(어댑터가 자기 config 주입 가능)."""
    en = PYRAMID_ENABLED if enabled is None else enabled
    mx = MAX_UNITS if max_units is None else max_units
    step = PYRAMID_STEP_N if step_n is None else step_n
    if not en or tracked.get("side") != "buy":
        return None
    if tracked.get("unit_count", 1) >= mx:
        return None
    N = tracked.get("n_at_entry") or tracked.get("atr") or 0
    if N <= 0 or not current_price:
        return None
    last = tracked.get("last_unit_price") or tracked.get("entry_price") or 0
    if current_price < last + step * N:
        return None
    qty_add = size_shares(account_value, N)
    if qty_add <= 0:
        return None
    old_qty = int(tracked.get("qty", 0) or 0)
    new_total = old_qty + qty_add
    new_stop = round(current_price - TURTLE_STOP_MULT * N, 2)
    return {"qty_add": qty_add, "new_total": new_total, "new_stop": new_stop,
            "new_risk": round(new_total * TURTLE_STOP_MULT * N, 2),
            "unit": tracked.get("unit_count", 1) + 1, "N": N}
