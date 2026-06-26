"""P0 회귀 테스트 — turtle_auto_trader (2026-06-27 red_team_block 후속).

검증 대상 4종:
  1. 체결 확인 게이트(wait_for_fill): 제출≠체결 — 미체결이면 포지션 미기록
  2. 손절 상주화: 체결 직후 브로커 stop 주문 상주 + state 에 stop_order_id 기록
  3. 고아 포지션 관리/유령 정리: reconcile_positions
  4. state 원자화: update_json_atomic 델타 적용(다른 writer 필드 보존)

모든 Alpaca 호출은 monkeypatch 로 차단(네트워크 없음).
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PAPER_TRADING_UNIVERSE", "SMH,SOXX,MU")

import scripts.turtle_auto_trader as t  # noqa: E402


@pytest.fixture(autouse=True)
def _tmp_state(tmp_path, monkeypatch):
    """STATE_PATH/LOG_PATH 를 임시 경로로 격리."""
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "positions.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "log.jsonl")
    yield


# ── 1. state 원자화 ───────────────────────────────────────────────────────────

def test_state_atomic_preserves_other_writer_fields():
    # 다른 writer 가 소유한 필드를 먼저 써둔다.
    t.STATE_PATH.write_text(json.dumps({"turtle_positions": {}, "other_writer": {"keep": 1}}))
    t.state_set_position("SMH", {"qty": 10, "stop_loss": 100.0})
    t.state_set_last_run("2026-06-27T00:00:00+00:00")
    data = json.loads(t.STATE_PATH.read_text())
    assert data["turtle_positions"]["SMH"]["qty"] == 10
    assert data["last_run"] == "2026-06-27T00:00:00+00:00"
    # 다른 writer 필드 보존(통째쓰기였다면 사라졌을 것)
    assert data["other_writer"] == {"keep": 1}
    t.state_pop_position("SMH")
    assert "SMH" not in json.loads(t.STATE_PATH.read_text())["turtle_positions"]
    assert json.loads(t.STATE_PATH.read_text())["other_writer"] == {"keep": 1}


# ── 2. 체결 확인 게이트 ────────────────────────────────────────────────────────

def test_wait_for_fill_returns_actual_fill(monkeypatch):
    seq = iter([
        {"status": "new", "filled_qty": "0"},
        {"status": "partially_filled", "filled_qty": "5"},
        {"status": "filled", "filled_qty": "10", "filled_avg_price": "123.45"},
    ])
    monkeypatch.setattr(t, "_alpaca_get", lambda path: next(seq))
    monkeypatch.setattr(t.time if hasattr(t, "time") else __import__("time"), "sleep", lambda *_: None)
    status, fq, fp = t.wait_for_fill("oid", timeout_s=10, poll_s=0)
    assert status == "filled" and fq == 10.0 and fp == 123.45


def test_enter_not_filled_does_not_record_position(monkeypatch):
    t.STATE_PATH.write_text(json.dumps({"turtle_positions": {}}))
    monkeypatch.setattr(t, "_alpaca_post", lambda path, body: {"id": "order-1"})
    # 체결 0 — 거절/미체결 시뮬
    monkeypatch.setattr(t, "wait_for_fill", lambda oid, **k: ("rejected", 0.0, 0.0))
    gate = {"shares": 10, "stop_loss": 95.0, "passed": True, "direction": "long",
            "system": "S2", "position_value": 1000, "risk_pct": 0.9}
    signal = {"current_price": 100.0, "atr": 2.5, "signal": "breakout_long"}
    state = {"turtle_positions": {}}
    res = t.enter_position("SMH", gate, signal, dry_run=False, state=state)
    assert res["status"] == "not_filled"
    # 유령 포지션이 만들어지지 않아야 한다
    assert "SMH" not in state["turtle_positions"]
    assert "SMH" not in json.loads(t.STATE_PATH.read_text()).get("turtle_positions", {})


# ── 2b. 손절 상주화 ───────────────────────────────────────────────────────────

def test_enter_places_resident_stop_and_records_id(monkeypatch):
    t.STATE_PATH.write_text(json.dumps({"turtle_positions": {}}))
    posted = []

    def fake_post(path, body):
        posted.append(body)
        return {"id": "buy-1" if body["side"] == "buy" else "stop-1"}

    monkeypatch.setattr(t, "_alpaca_post", fake_post)
    monkeypatch.setattr(t, "wait_for_fill", lambda oid, **k: ("filled", 10.0, 100.0))
    monkeypatch.setattr(t, "log_trade_entry", lambda **k: None)
    gate = {"shares": 10, "stop_loss": 95.0, "passed": True, "direction": "long",
            "system": "S2", "position_value": 1000, "risk_pct": 0.9}
    signal = {"current_price": 100.0, "atr": 2.5, "signal": "breakout_long"}
    state = {"turtle_positions": {}}
    res = t.enter_position("SMH", gate, signal, dry_run=False, state=state)
    assert res["status"] == "filled"
    # 손절가는 체결가 100 - 2*2.5 = 95.0
    assert res["stop_loss"] == 95.0
    # 두 번째 주문이 stop 매도 상주 주문이어야 한다
    stop_orders = [b for b in posted if b.get("type") == "stop"]
    assert len(stop_orders) == 1
    assert stop_orders[0]["side"] == "sell" and float(stop_orders[0]["stop_price"]) == 95.0
    saved = json.loads(t.STATE_PATH.read_text())["turtle_positions"]["SMH"]
    assert saved["stop_order_id"] == "stop-1" and saved["qty"] == 10


# ── 3. 고아 입양 / 유령 정리 ──────────────────────────────────────────────────

def test_reconcile_adopts_orphan_in_universe(monkeypatch):
    t.STATE_PATH.write_text(json.dumps({"turtle_positions": {}}))
    posted = []
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: posted.append(b) or {"id": "stop-x"})
    # ATR 계산 우회
    monkeypatch.setattr(t, "_get_bars", lambda s, days=25: [{"h": 1, "l": 1, "c": 1}] * 30)
    monkeypatch.setattr(t, "_calc_atr", lambda bars, p: 3.0)
    orphan = next(iter({s.strip().upper() for s in t.UNIVERSE}))  # 실제 유니버스 내 종목
    positions = [{"symbol": orphan, "qty": 5, "entry_price": 200.0, "current_price": 195.0, "atr": 0}]
    state = {"turtle_positions": {}}
    acts = t.reconcile_positions(positions, state, dry_run=False)
    assert any(a["action"] == "adopt_orphan" and a["symbol"] == orphan for a in acts)
    # 입양 시 상주 손절(200 - 2*3 = 194) 주문이 나가야 한다
    assert any(b.get("type") == "stop" and float(b["stop_price"]) == 194.0 for b in posted)
    assert state["turtle_positions"][orphan]["adopted"] is True


def test_reconcile_skips_manual_non_universe(monkeypatch):
    t.STATE_PATH.write_text(json.dumps({"turtle_positions": {}}))
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: {"id": "x"})
    positions = [{"symbol": "AAPL", "qty": 5, "entry_price": 200.0, "current_price": 195.0, "atr": 1}]
    state = {"turtle_positions": {}}
    acts = t.reconcile_positions(positions, state, dry_run=False)
    # 유니버스(SMH/SOXX/MU)에 없는 AAPL 은 입양하지 않는다
    assert not acts
    assert "AAPL" not in state["turtle_positions"]


def test_reconcile_cleans_ghost_and_cancels_stop(monkeypatch):
    canceled = []
    monkeypatch.setattr(t, "cancel_order", lambda oid: canceled.append(oid))
    monkeypatch.setattr(t, "log_trade_exit", lambda **k: None)
    t.STATE_PATH.write_text(json.dumps({"turtle_positions": {
        "SMH": {"qty": 10, "entry_price": 100, "stop_loss": 95, "stop_order_id": "stop-9"}
    }}))
    state = json.loads(t.STATE_PATH.read_text())
    # 브로커 포지션 비어있음 → SMH 는 유령
    acts = t.reconcile_positions([], state, dry_run=False)
    assert any(a["action"] == "ghost_reconcile" and a["symbol"] == "SMH" for a in acts)
    assert "stop-9" in canceled
    assert "SMH" not in state["turtle_positions"]
    assert "SMH" not in json.loads(t.STATE_PATH.read_text())["turtle_positions"]


def test_reconcile_dry_run_no_side_effects(monkeypatch):
    canceled = []
    monkeypatch.setattr(t, "cancel_order", lambda oid: canceled.append(oid))
    monkeypatch.setattr(t, "_alpaca_post", lambda p, b: (_ for _ in ()).throw(AssertionError("no post in dry_run")))
    t.STATE_PATH.write_text(json.dumps({"turtle_positions": {
        "SMH": {"qty": 10, "entry_price": 100, "stop_loss": 95, "stop_order_id": "stop-9"}
    }}))
    state = json.loads(t.STATE_PATH.read_text())
    t.reconcile_positions([], state, dry_run=True)
    # dry_run 은 브로커 호출/취소 없이 in-memory 만 정리
    assert canceled == []
    assert json.loads(t.STATE_PATH.read_text())["turtle_positions"].get("SMH") is not None
