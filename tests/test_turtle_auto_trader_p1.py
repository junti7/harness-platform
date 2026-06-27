"""P1 회귀 테스트 — turtle_auto_trader (2026-06-27 진단 F1/F2/F3).

  F3 사이징: 손절거리(2N) 기준 → 실효 리스크 ≤1% (기존 1N 사이징의 절반)
  F2 상관 한도: 동등 ETF 동시보유 차단 + 상관 그룹 유닛 상한
  F1 추세필터: 장기 MA 위에서만 롱 진입
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.turtle_auto_trader as t  # noqa: E402


# ── F3 사이징 ─────────────────────────────────────────────────────────────────

def test_sizing_1N_classic_with_2N_risk_reporting():
    """2026-06-27 CEO 확정: 1N 사이징(클래식). 측정은 2N(실효 ~2%), 게이트 ≤2%."""
    acct = 100_000.0
    atr = 2.5
    sig = {"symbol": "NVDA", "current_price": 100.0, "atr": atr,
           "signal": "breakout_long", "system": "S2", "direction": "long"}
    g = t.turtle_gate_check(sig, acct)
    # 1N 사이징: shares = 100000*0.01/2.5 = 400
    assert g["shares"] == 400
    # 실효 손절 리스크(2N) = 400*5 = $2000 = 2.0% — 측정은 항상 2N 기준
    assert abs(g["risk_pct"] - 2.0) < 0.06
    # ≤2%(TURTLE_MAX_RISK_PCT) 게이트 통과
    assert g["checks"]["risk_pct"] is True
    assert g["stop_loss"] == 95.0


def test_sizing_gate_blocks_above_2pct(monkeypatch):
    """단일 트레이드 상한 2% 초과는 게이트 차단."""
    monkeypatch.setattr(t, "TURTLE_MAX_RISK_PCT", 0.015)  # 1.5%로 낮추면 2% 사이징은 막혀야
    acct, atr = 100_000.0, 2.5
    sig = {"symbol": "NVDA", "current_price": 100.0, "atr": atr,
           "signal": "breakout_long", "system": "S2", "direction": "long"}
    g = t.turtle_gate_check(sig, acct)
    assert g["risk_pct"] > 1.5
    assert g["checks"]["risk_pct"] is False


def test_portfolio_heat():
    acct = 100_000.0
    state = {"turtle_positions": {
        "A": {"qty": 100, "entry_price": 50.0, "stop_loss": 40.0},   # risk 100*10=1000=1%
        "B": {"qty": 50, "entry_price": 100.0, "stop_loss": 80.0},   # risk 50*20=1000=1%
    }}
    assert abs(t.portfolio_heat(state, acct) - 0.02) < 1e-9
    assert t.portfolio_heat(state, 0) == 0.0


# ── F2 상관 한도 ──────────────────────────────────────────────────────────────

def test_equivalent_etf_blocked():
    # SMH 보유 중이면 SOXX(동일 ETF) 진입 차단
    blocked, reason = t.correlation_block("SOXX", held={"SMH"})
    assert blocked and "equivalent_etf_held" in reason
    # 역방향도
    blocked, _ = t.correlation_block("SMH", held={"SOXX"})
    assert blocked


def test_corr_group_cap(monkeypatch):
    monkeypatch.setattr(t, "MAX_UNITS_PER_GROUP", 3)
    # SEMI 그룹 3개 보유 → 4번째 SEMI 차단
    held = {"NVDA", "TSM", "MU"}  # 모두 SEMI
    blocked, reason = t.correlation_block("AVGO", held=held)
    assert blocked and "corr_group_full" in reason
    # 다른 그룹(POWER)은 통과
    blocked2, _ = t.correlation_block("VRT", held=held)
    assert not blocked2


def test_corr_block_allows_when_room():
    blocked, _ = t.correlation_block("NVDA", held={"TSLA"})  # AUTO 1개뿐
    assert not blocked


def test_should_enter_applies_correlation(monkeypatch):
    monkeypatch.setattr(t, "passes_trend_filter", lambda s, p: (True, "ok"))
    sig = {"signal": "breakout_long", "current_price": 600.0, "atr": 20.0, "symbol": "SOXX"}
    state = {"turtle_positions": {"SMH": {}}}
    ok, reason = t.should_enter("SOXX", sig, existing_symbols=set(), state=state)
    assert not ok and "correlation_block" in reason


# ── F1 추세필터 ───────────────────────────────────────────────────────────────

def test_trend_filter_blocks_below_ma(monkeypatch):
    monkeypatch.setattr(t, "TREND_FILTER_ENABLED", True)
    monkeypatch.setattr(t, "TREND_MA_DAYS", 5)
    # 종가 평균 100, 현재가 90 → 아래 → 차단
    monkeypatch.setattr(t, "_get_bars", lambda s, days=120: [{"c": 100}] * 20)
    ok, note = t.passes_trend_filter("NVDA", 90.0)
    assert not ok and "below_ma" in note
    # 현재가 110 → 위 → 통과
    ok2, note2 = t.passes_trend_filter("NVDA", 110.0)
    assert ok2 and "above_ma" in note2


def test_trend_filter_failopen_insufficient(monkeypatch):
    monkeypatch.setattr(t, "TREND_FILTER_ENABLED", True)
    monkeypatch.setattr(t, "TREND_MA_DAYS", 100)
    monkeypatch.setattr(t, "_get_bars", lambda s, days=120: [{"c": 100}] * 10)  # 부족
    ok, note = t.passes_trend_filter("NVDA", 1.0)
    assert ok and "insufficient_bars_failopen" in note


def test_trend_filter_off(monkeypatch):
    monkeypatch.setattr(t, "TREND_FILTER_ENABLED", False)
    ok, note = t.passes_trend_filter("NVDA", 1.0)
    assert ok and note == "filter_off"


def test_should_enter_blocks_on_trend(monkeypatch):
    monkeypatch.setattr(t, "correlation_block", lambda s, h: (False, ""))
    monkeypatch.setattr(t, "passes_trend_filter", lambda s, p: (False, "below_ma100(...)"))
    sig = {"signal": "breakout_long", "current_price": 90.0, "atr": 2.0, "symbol": "NVDA"}
    state = {"turtle_positions": {}}
    ok, reason = t.should_enter("NVDA", sig, existing_symbols=set(), state=state)
    assert not ok and "trend_filter" in reason
