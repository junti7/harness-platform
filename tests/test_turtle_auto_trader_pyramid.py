"""#2 피라미딩 회귀 테스트 — turtle_auto_trader (2026-06-27, 롱 전용).

  - ½N 유리 이동 시 유닛 추가, 미달이면 추가 안 함
  - 최대 유닛 상한 / heat 상한 / 숏(side!=buy) 미적용
  - 유닛 추가 시 손절 상향 + 상주손절 교체 + state 갱신
모든 Alpaca 호출은 monkeypatch.
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scripts.turtle_auto_trader as t  # noqa: E402


@pytest.fixture(autouse=True)
def _tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "positions.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "log.jsonl")
    monkeypatch.setattr(t, "PAPER_PYRAMID_ENABLED", True)
    monkeypatch.setattr(t, "PAPER_MAX_UNITS", 4)
    monkeypatch.setattr(t, "PAPER_PYRAMID_STEP_N", 0.5)
    monkeypatch.setattr(t, "PAPER_MAX_PORTFOLIO_HEAT", 1.0)  # heat 무제한(별도 테스트서 검증)
    t.STATE_PATH.write_text(json.dumps({"turtle_positions": {}}))
    yield


def _pos(sym, entry, N, qty, stop, units=1, last=None, stop_id="s0"):
    return {sym: {"side": "buy", "entry_price": entry, "n_at_entry": N, "atr": N,
                  "qty": qty, "stop_loss": stop, "unit_count": units,
                  "last_unit_price": last or entry, "stop_order_id": stop_id,
                  "risk_usd": qty * 2 * N}}


def _broker(sym, cur, qty):
    return [{"symbol": sym, "current_price": cur, "qty": qty}]


def test_pyramid_adds_on_half_N_move(monkeypatch):
    posted = []
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: posted.append(b) or {"id": "buy1" if b["side"] == "buy" else "stop1"})
    monkeypatch.setattr(t, "wait_for_fill", lambda oid, **k: ("filled", 40.0, 110.0))
    monkeypatch.setattr(t, "cancel_order", lambda oid: None)
    monkeypatch.setattr(t, "log_trade_entry", lambda **k: None)
    state = {"turtle_positions": _pos("NVDA", entry=100.0, N=10.0, qty=40, stop=80.0)}
    # 진입가 100, N=10 → ½N=5 → 트리거 105. 현재가 110 ≥ 트리거 → 추가
    acts = t.pyramid_positions(_broker("NVDA", 110.0, 40), state, account_value=100000, dry_run=False)
    assert any(a["action"] == "pyramid_add" for a in acts)
    p = state["turtle_positions"]["NVDA"]
    assert p["unit_count"] == 2
    assert p["qty"] == 80                       # 40 + 40
    assert p["stop_loss"] == 90.0               # 110 - 2*10 (손절 상향: 80→90)
    # 매수 + 상주손절 교체(신규 stop) 주문이 나갔다
    assert any(b["type"] == "stop" and float(b["stop_price"]) == 90.0 and b["qty"] == "80" for b in posted)


def test_pyramid_no_add_below_trigger(monkeypatch):
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: (_ for _ in ()).throw(AssertionError("no order")))
    state = {"turtle_positions": _pos("NVDA", entry=100.0, N=10.0, qty=40, stop=80.0)}
    # 현재가 104 < 트리거 105 → 추가 안 함
    acts = t.pyramid_positions(_broker("NVDA", 104.0, 40), state, account_value=100000, dry_run=False)
    assert acts == []
    assert state["turtle_positions"]["NVDA"]["unit_count"] == 1


def test_pyramid_respects_max_units(monkeypatch):
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: (_ for _ in ()).throw(AssertionError("no order")))
    state = {"turtle_positions": _pos("NVDA", 100.0, 10.0, 160, 80.0, units=4, last=120.0)}
    acts = t.pyramid_positions(_broker("NVDA", 200.0, 160), state, account_value=100000, dry_run=False)
    assert acts == []  # 이미 4유닛


def test_pyramid_skips_short_side(monkeypatch):
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: (_ for _ in ()).throw(AssertionError("no order")))
    state = {"turtle_positions": {"NVDA": {"side": "sell", "n_at_entry": 10, "qty": 40,
                                           "entry_price": 100, "last_unit_price": 100,
                                           "unit_count": 1, "stop_loss": 120}}}
    acts = t.pyramid_positions(_broker("NVDA", 80.0, 40), state, account_value=100000, dry_run=False)
    assert acts == []  # 숏은 피라미딩 미적용


def test_pyramid_heat_cap_blocks(monkeypatch):
    monkeypatch.setattr(t, "PAPER_MAX_PORTFOLIO_HEAT", 0.015)  # 1.5% 상한
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: (_ for _ in ()).throw(AssertionError("no order")))
    # 기존 risk 0.8% + 추가 시 총 risk_usd 커져 1.5% 초과 → 차단
    state = {"turtle_positions": _pos("NVDA", 100.0, 10.0, 40, 80.0)}  # risk_usd=40*20=800=0.8%
    acts = t.pyramid_positions(_broker("NVDA", 110.0, 40), state, account_value=100000, dry_run=False)
    assert any(a["action"] == "pyramid_skip" and a["reason"] == "heat_cap" for a in acts)
    assert state["turtle_positions"]["NVDA"]["unit_count"] == 1


def test_pyramid_dry_run_no_orders(monkeypatch):
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: (_ for _ in ()).throw(AssertionError("no order in dry_run")))
    state = {"turtle_positions": _pos("NVDA", 100.0, 10.0, 40, 80.0)}
    acts = t.pyramid_positions(_broker("NVDA", 110.0, 40), state, account_value=100000, dry_run=True)
    assert any(a["status"] == "dry_run" for a in acts)
    # dry_run 은 in-memory 만 반영(브로커 주문 없음)
    assert state["turtle_positions"]["NVDA"]["unit_count"] == 2


def test_pyramid_disabled(monkeypatch):
    monkeypatch.setattr(t, "PAPER_PYRAMID_ENABLED", False)
    state = {"turtle_positions": _pos("NVDA", 100.0, 10.0, 40, 80.0)}
    assert t.pyramid_positions(_broker("NVDA", 110.0, 40), state, 100000, False) == []
