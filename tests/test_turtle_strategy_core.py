"""core/turtle_strategy.py 검증 — 직접 단위테스트 + 현행 Alpaca 트레이더와의 parity(동치).

페이즈 B(IBKR 일원화) B1: core 는 검증된 turtle_auto_trader 로직의 충실한 포팅이다. parity 테스트로
'core ≡ 트레이더' 를 증명하면, IBKR 가 core 를 써도 동일하게 검증된 로직이 보장된다.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import core.turtle_strategy as core  # noqa: E402
import scripts.turtle_auto_trader as t  # noqa: E402


# ── core 직접 단위테스트 ──────────────────────────────────────────────────────

def _bars(prices, atr_h=1.0):
    """종가 리스트로 OHLC bars 생성(h/l = c±atr_h)."""
    return [{"o": c, "h": c + atr_h, "l": c - atr_h, "c": c, "t": f"2026-01-{i+1:02d}"}
            for i, c in enumerate(prices)]


def test_core_compute_atr():
    bars = _bars([100] * 30, atr_h=1.5)  # TR=3 매일 → ATR=3
    assert abs(core.compute_atr(bars, 20) - 3.0) < 1e-9


def test_core_signal_breakout_long():
    prices = [100] * 60 + [130]  # 마지막이 직전 55/20일 고가 돌파
    sig = core.signal_from_bars("NVDA", _bars(prices))
    assert sig["signal"] == "breakout_long" and sig["system"] == "S2" and sig["direction"] == "long"


def test_core_signal_insufficient():
    assert core.signal_from_bars("X", _bars([100] * 10))["signal"] == "insufficient_data"


def test_core_sizing_1N_and_gate():
    sig = {"symbol": "NVDA", "current_price": 100.0, "atr": 2.5,
           "signal": "breakout_long", "system": "S2", "direction": "long"}
    g = core.turtle_gate_check(sig, 100_000)
    assert g["shares"] == 400 and abs(g["risk_pct"] - 2.0) < 0.06 and g["passed"]


def test_core_gate_injected_max_risk_blocks():
    sig = {"symbol": "NVDA", "current_price": 100.0, "atr": 2.5,
           "signal": "breakout_long", "system": "S2", "direction": "long"}
    g = core.turtle_gate_check(sig, 100_000, max_risk_pct=0.015)
    assert g["checks"]["risk_pct"] is False


def test_core_correlation_and_heat():
    assert core.correlation_block("SOXX", {"SMH"})[0]
    assert core.correlation_block("QQQ", {"NVDA", "SMH", "MU"})[0]  # SEMI 3개
    assert not core.correlation_block("TLT", {"NVDA", "SMH", "MU"})[0]  # BOND 독립
    heat = core.portfolio_heat({"A": {"risk_usd": 2000}, "B": {"qty": 50, "entry_price": 100, "stop_loss": 80}}, 100_000)
    assert abs(heat - 0.03) < 1e-9  # 2000 + 50*20=1000 = 3000/100k


def test_core_trend_and_exit():
    assert core.trend_filter_ok([100] * 100, 110)[0]
    assert not core.trend_filter_ok([100] * 100, 90)[0]
    bars = _bars([100] * 20 + [80])  # 마지막이 직전 10/20일 저가 이탈
    assert core.exit_signal(bars, "S2", "long")[0]
    bars_s = _bars([100] * 20 + [130])
    assert core.exit_signal(bars_s, "S2", "short")[0]


def test_core_pyramid_decision():
    tracked = {"side": "buy", "n_at_entry": 10, "entry_price": 100, "last_unit_price": 100,
               "unit_count": 1, "qty": 40}
    d = core.pyramid_decision(tracked, 110, 100_000)  # ½N=5 → 트리거 105, 110≥105
    # qty_add = 100000*1%/N(10) = 100 → new_total = 40+100 = 140
    assert d and d["new_total"] == 140 and d["new_stop"] == 90.0 and d["unit"] == 2
    assert core.pyramid_decision(tracked, 104, 100_000) is None  # 트리거 미달
    assert core.pyramid_decision({**tracked, "side": "sell"}, 110, 100_000) is None  # 숏 제외


# ── parity: core ≡ 현행 Alpaca 트레이더 ───────────────────────────────────────

def test_parity_gate_check():
    for atr in (2.5, 7.89, 36.09):
        sig = {"symbol": "NVDA", "current_price": 100.0 + atr, "atr": atr,
               "signal": "breakout_long", "system": "S2", "direction": "long"}
        c = core.turtle_gate_check(sig, 94_000, max_risk_pct=t.TURTLE_MAX_RISK_PCT)
        a = t.turtle_gate_check(sig, 94_000)
        assert c["shares"] == a["shares"]
        assert abs(c["risk_pct"] - a["risk_pct"]) < 1e-6
        assert c["stop_loss"] == a["stop_loss"]


def test_parity_correlation_block():
    cases = [("SOXX", {"SMH"}), ("QQQ", {"NVDA", "SMH", "MU"}), ("TLT", {"NVDA", "SMH"}),
             ("META", {"GOOG"}), ("VRT", {"NVDA"})]
    for sym, held in cases:
        c = core.correlation_block(sym, held, t.CORR_GROUP, t.EQUIVALENT_ETF_SETS, t.MAX_UNITS_PER_GROUP)
        a = t.correlation_block(sym, held)
        assert c[0] == a[0], f"{sym} {held}: core={c} trader={a}"


def test_parity_portfolio_heat():
    positions = {"X": {"qty": 100, "entry_price": 50, "stop_loss": 40}, "Y": {"risk_usd": 1500}}
    # core 는 positions 직접, 트레이더는 state 래퍼({"turtle_positions": positions})
    c = core.portfolio_heat(positions, 100_000)
    a = t.portfolio_heat({"turtle_positions": positions}, 100_000)
    assert abs(c - a) < 1e-9


def test_parity_corr_group_map_matches():
    # core 와 트레이더의 상관그룹 맵이 동일해야(드리프트 방지)
    assert core.CORR_GROUP == t.CORR_GROUP
    assert core.EQUIVALENT_ETF_SETS == t.EQUIVALENT_ETF_SETS
    assert core.DIVERSIFIERS == t.DIVERSIFIERS
