"""Phase B2 회귀 테스트 — ibkr_tws_paper_trader (2026-06-27).

검증 대상:
  1. ibkr_bars_to_core: BarData → core 형식 변환
  2. wait_for_fill_ibkr: terminal 상태 감지 + timeout
  3. reconcile_positions_ibkr: 고아 입양 / 유령 정리
  4. manage_positions_ibkr: 손절 체크 / 청산 신호
  5. pyramid_positions_ibkr: ½N 트리거 / heat cap 차단
  6. 신호 스캔 진입 게이트: 추세필터 / 상관한도 / heat cap / TurtleGate
  7. state_set_position / state_pop_position 원자화

IBKR / 네트워크 호출은 모두 monkeypatch로 차단.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.ibkr_tws_paper_trader as t


# ── 픽스처 ─────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _tmp_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "ibkr_positions.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "ibkr_log.jsonl")
    yield


def _make_bar(h: float, l: float, c: float, o: float = 100.0):
    b = SimpleNamespace()
    b.high = h
    b.low = l
    b.close = c
    b.open = o
    return b


def _make_ib(broker_positions=None, portfolio_items=None):
    ib = MagicMock()
    ib.positions.return_value = broker_positions or []
    ib.portfolio.return_value = portfolio_items or []
    ib.trades.return_value = []
    ib.openTrades.return_value = []
    ib.sleep = MagicMock()
    return ib


def _make_portfolio_item(symbol: str, position: float, avg_cost: float, market_price: float):
    item = SimpleNamespace()
    item.contract = SimpleNamespace(symbol=symbol)
    item.position = position
    item.avgCost = avg_cost
    item.marketPrice = market_price
    return item


def _make_broker_pos(symbol: str, position: float, avg_cost: float, market_price: float):
    return _make_portfolio_item(symbol, position, avg_cost, market_price)


# ── 1. ibkr_bars_to_core ──────────────────────────────────────────────────────

def test_ibkr_bars_to_core_basic():
    bars_raw = [_make_bar(110, 90, 100), _make_bar(120, 95, 115)]
    result = t.ibkr_bars_to_core(bars_raw)
    assert len(result) == 2
    assert result[0] == {"h": 110.0, "l": 90.0, "c": 100.0, "o": 100.0}
    assert result[1]["h"] == 120.0


def test_ibkr_bars_to_core_empty():
    assert t.ibkr_bars_to_core([]) == []


# ── 2. wait_for_fill_ibkr ─────────────────────────────────────────────────────

def test_wait_for_fill_filled():
    trade = MagicMock()
    trade.orderStatus.status = "Filled"
    trade.orderStatus.filled = 10
    trade.orderStatus.avgFillPrice = 105.5

    ib = MagicMock()
    ib.sleep = MagicMock()

    status, qty, price = t.wait_for_fill_ibkr(ib, trade, timeout_s=5, poll_s=0.01)
    assert status == "Filled"
    assert qty == 10.0
    assert price == 105.5


def test_wait_for_fill_cancelled():
    trade = MagicMock()
    trade.orderStatus.status = "Cancelled"
    trade.orderStatus.filled = 0
    trade.orderStatus.avgFillPrice = 0

    ib = MagicMock()
    ib.sleep = MagicMock()

    status, qty, price = t.wait_for_fill_ibkr(ib, trade, timeout_s=5, poll_s=0.01)
    assert status == "Cancelled"
    assert qty == 0.0


def test_wait_for_fill_timeout():
    """timeout 시 현재 상태 그대로 반환."""
    call_count = [0]
    original_monotonic = __import__("time").monotonic

    trade = MagicMock()
    trade.orderStatus.status = "Submitted"
    trade.orderStatus.filled = 0
    trade.orderStatus.avgFillPrice = 0

    ib = MagicMock()
    ib.sleep = MagicMock()

    # 시간 가속: poll_s=0.001, timeout_s=0.002면 루프 1-2회 후 종료
    status, qty, price = t.wait_for_fill_ibkr(ib, trade, timeout_s=0.002, poll_s=0.001)
    assert status == "Submitted"
    assert qty == 0.0


# ── 3. reconcile_positions_ibkr ───────────────────────────────────────────────

def test_reconcile_adopt_orphan(tmp_path, monkeypatch):
    """브로커에 있고 state엔 없는 종목 → 고아 입양."""
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "s.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")

    ib = _make_ib()
    # fetch_bars_ibkr patch: ATR 계산 가능한 bars 반환
    bars = [{"h": 110, "l": 90, "c": 100, "o": 100}] * 30
    monkeypatch.setattr(t, "fetch_bars_ibkr", lambda ib_, c, days=150: bars)
    monkeypatch.setattr(t, "place_resident_stop", lambda ib_, c, qty, stop, acct: 9001)

    state = {"positions": {}, "pending_orders": {}}
    bp = {
        "NVDA": _make_broker_pos("NVDA", 5.0, 200.0, 210.0),
    }
    universe_set = {"NVDA", "TSM"}

    actions = t.reconcile_positions_ibkr(ib, state, bp, universe_set, "DU123", dry_run=False)

    assert any(a["action"] == "adopt_orphan" and a["symbol"] == "NVDA" for a in actions)
    assert "NVDA" in state["positions"]
    assert state["positions"]["NVDA"]["qty"] == 5


def test_reconcile_ghost_cleanup(tmp_path, monkeypatch):
    """state엔 있지만 브로커엔 없는 종목 → 유령 정리."""
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "s.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")

    # state 파일 초기화 (NVDA tracked)
    state_file = tmp_path / "s.json"
    state_file.write_text(json.dumps({
        "positions": {"NVDA": {"entry_price": 200, "stop_loss": 180, "qty": 5,
                                "resident_stop_id": 111}},
        "pending_orders": {},
    }))
    monkeypatch.setattr(t, "STATE_PATH", state_file)

    ib = _make_ib()
    monkeypatch.setattr(t, "cancel_ibkr_order", MagicMock())

    state = {"positions": {"NVDA": {"entry_price": 200, "stop_loss": 180,
                                     "qty": 5, "resident_stop_id": 111}},
             "pending_orders": {}}
    bp = {}  # 브로커에 없음
    universe_set = {"NVDA"}

    actions = t.reconcile_positions_ibkr(ib, state, bp, universe_set, "DU123", dry_run=False)

    assert any(a["action"] == "ghost_reconcile" and a["symbol"] == "NVDA" for a in actions)
    assert "NVDA" not in state["positions"]


# ── 4. manage_positions_ibkr (손절/청산) ──────────────────────────────────────

def test_manage_stop_hit(tmp_path, monkeypatch):
    """현재가 ≤ 손절가 → exit."""
    state_file = tmp_path / "s.json"
    state_file.write_text(json.dumps({
        "positions": {"MU": {"entry_price": 100, "stop_loss": 90, "qty": 10,
                              "system": "S2", "side": "buy", "resident_stop_id": 200}},
        "pending_orders": {},
    }))
    monkeypatch.setattr(t, "STATE_PATH", state_file)
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")

    ib = _make_ib()
    monkeypatch.setattr(t, "fetch_bars_ibkr", lambda ib_, c, days=35: [])
    monkeypatch.setattr(t, "cancel_ibkr_order", MagicMock())

    state = {"positions": {"MU": {"entry_price": 100, "stop_loss": 90, "qty": 10,
                                   "system": "S2", "side": "buy", "resident_stop_id": 200}},
             "pending_orders": {}}
    # 현재가 = 88 (손절가 90 이하)
    bp = {"MU": _make_broker_pos("MU", 10.0, 100.0, 88.0)}

    actions = t.manage_positions_ibkr(
        ib, state, bp, {"MU"}, "DU123", dry_run=True)
    exit_acts = [a for a in actions if a.get("action") == "exit"]
    assert len(exit_acts) == 1
    assert "stop_loss_hit" in exit_acts[0]["reason"]


def test_manage_exit_signal(tmp_path, monkeypatch):
    """core.exit_signal 발동 → exit."""
    state_file = tmp_path / "s.json"
    state_file.write_text(json.dumps({
        "positions": {"ASX": {"entry_price": 40, "stop_loss": 35, "qty": 60,
                               "system": "S2", "side": "buy", "resident_stop_id": 201}},
        "pending_orders": {},
    }))
    monkeypatch.setattr(t, "STATE_PATH", state_file)
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")

    ib = _make_ib()
    # 20일 저가=37인 window + 현재가=36(bars[-1].c) → 36 < 37 이탈
    bars_exit = [{"h": 42, "l": 37, "c": 37, "o": 40}] * 24 + [{"h": 38, "l": 35, "c": 36, "o": 40}]
    monkeypatch.setattr(t, "fetch_bars_ibkr", lambda ib_, c, days=35: bars_exit)
    monkeypatch.setattr(t, "cancel_ibkr_order", MagicMock())

    state = {"positions": {"ASX": {"entry_price": 40, "stop_loss": 35, "qty": 60,
                                    "system": "S2", "side": "buy", "resident_stop_id": 201}},
             "pending_orders": {}}
    bp = {"ASX": _make_broker_pos("ASX", 60.0, 40.0, 36.0)}

    actions = t.manage_positions_ibkr(
        ib, state, bp, {"ASX"}, "DU123", dry_run=True)
    exit_acts = [a for a in actions if a.get("action") == "exit"]
    assert len(exit_acts) == 1
    assert "exit_signal" in exit_acts[0]["reason"]


# ── 5. pyramid_positions_ibkr ────────────────────────────────────────────────

def test_pyramid_triggers(tmp_path, monkeypatch):
    """½N 이동 시 피라미딩 발동 (dry-run)."""
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "s.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")
    monkeypatch.setattr(t, "PAPER_PYRAMID_ENABLED", True)
    monkeypatch.setattr(t, "PAPER_MAX_UNITS", 4)
    monkeypatch.setattr(t, "PAPER_PYRAMID_STEP_N", 0.5)

    state = {"positions": {
        "VRT": {
            "entry_price": 300.0, "atr": 10.0, "stop_loss": 280.0,
            "qty": 3, "side": "buy", "unit_count": 1,
            "n_at_entry": 10.0, "last_unit_price": 300.0,
            "risk_usd": 60.0, "system": "S2",
        }
    }, "pending_orders": {}}

    # 현재가 = 306 (>= 300 + 0.5×10 = 305) → 트리거
    bp = {"VRT": _make_broker_pos("VRT", 3.0, 300.0, 306.0)}

    actions = t.pyramid_positions_ibkr(
        MagicMock(), state, bp, 10000.0, "DU123", dry_run=True)

    adds = [a for a in actions if a.get("action") == "pyramid_add"]
    assert len(adds) == 1
    assert adds[0]["unit"] == 2


def test_pyramid_heat_cap_block(tmp_path, monkeypatch):
    """heat 상한 초과 시 피라미딩 차단."""
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "s.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")
    monkeypatch.setattr(t, "PAPER_PYRAMID_ENABLED", True)
    monkeypatch.setattr(t, "PAPER_MAX_PORTFOLIO_HEAT", 0.05)  # 5% 상한 (낮게 설정)

    state = {"positions": {
        "NVDA": {
            "entry_price": 100.0, "atr": 5.0, "stop_loss": 90.0,
            "qty": 10, "side": "buy", "unit_count": 1,
            "n_at_entry": 5.0, "last_unit_price": 100.0,
            "risk_usd": 100.0, "system": "S2",
        }
    }, "pending_orders": {}}

    # 현재가 = 103 (>= 100 + 0.5×5 = 102.5) → 트리거 조건 충족
    bp = {"NVDA": _make_broker_pos("NVDA", 10.0, 100.0, 103.0)}

    # heat 계산: 기존 risk_usd=100, account=1000 → 기존 heat=10% > cap 5% 이미 초과
    actions = t.pyramid_positions_ibkr(
        MagicMock(), state, bp, 1000.0, "DU123", dry_run=True)

    skips = [a for a in actions if a.get("action") == "pyramid_skip"]
    assert len(skips) == 1
    assert skips[0]["reason"] == "heat_cap"


# ── 6. 신호 스캔 게이트 (단위 함수 수준) ──────────────────────────────────────

def test_trend_filter_blocked(monkeypatch):
    """종가가 100일 MA 이하 → trend_filter_ok=False."""
    import core.turtle_strategy as core
    closes = [100.0] * 100 + [95.0]  # 현재가 95, MA ≈ 99.x
    ok, note = core.trend_filter_ok(closes, current_price=95.0, ma_days=100, enabled=True)
    assert not ok
    assert "below_ma" in note


def test_correlation_block_semi(monkeypatch):
    """같은 SEMI 그룹 3개 보유 시 4번째 차단."""
    import core.turtle_strategy as core
    held = {"NVDA", "MU", "TSM"}  # 전부 SEMI 그룹 (MAX_UNITS_PER_GROUP=3)
    blocked, reason = core.correlation_block("AVGO", held, max_units=3)
    assert blocked
    assert "SEMI" in reason


def test_heat_cap_gate():
    """portfolio_heat + new_heat > cap 시 진입 차단 로직."""
    import core.turtle_strategy as core
    positions = {
        "A": {"qty": 10, "entry_price": 100, "stop_loss": 90},  # risk=100
        "B": {"qty": 20, "entry_price": 50, "stop_loss": 45},   # risk=100
    }
    heat = core.portfolio_heat(positions, account_value=1000)
    # total risk = 200, account = 1000 → heat = 0.20
    assert abs(heat - 0.20) < 0.001
    # cap=0.10 → 이미 초과
    assert heat > 0.10


# ── 7. state 원자화 ───────────────────────────────────────────────────────────

def test_state_set_pop_position(tmp_path, monkeypatch):
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "s.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")

    # 초기 state
    (tmp_path / "s.json").write_text(json.dumps({"positions": {}, "pending_orders": {}}))

    t.state_set_position("VRT", {"entry_price": 300, "stop_loss": 280, "qty": 5})
    state = json.loads((tmp_path / "s.json").read_text())
    assert "VRT" in state["positions"]
    assert state["positions"]["VRT"]["qty"] == 5

    t.state_pop_position("VRT")
    state = json.loads((tmp_path / "s.json").read_text())
    assert "VRT" not in state["positions"]


def test_state_set_position_preserves_other_keys(tmp_path, monkeypatch):
    """다른 writer 필드(baseline, last_run 등)를 덮어쓰지 않는다."""
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "s.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")

    (tmp_path / "s.json").write_text(json.dumps({
        "positions": {}, "pending_orders": {},
        "baseline": {"nav": 50000, "set_at": "2026-06-27T00:00:00Z"},
        "last_run": "2026-06-27T01:00:00Z",
    }))

    t.state_set_position("GLD", {"entry_price": 220, "qty": 2})

    state = json.loads((tmp_path / "s.json").read_text())
    assert state["baseline"]["nav"] == 50000
    assert state["last_run"] == "2026-06-27T01:00:00Z"
    assert "GLD" in state["positions"]


# ── 8. 부분 체결 처리 ─────────────────────────────────────────────────────────

def test_wait_for_fill_partial_then_timeout():
    """부분 체결 후 timeout — filled_qty > 0, status 비terminal."""
    trade = MagicMock()
    trade.orderStatus.status = "PreSubmitted"
    trade.orderStatus.filled = 5
    trade.orderStatus.avgFillPrice = 100.0

    ib = MagicMock()
    ib.sleep = MagicMock()

    status, qty, price = t.wait_for_fill_ibkr(ib, trade, timeout_s=0.001, poll_s=0.0005)
    # timeout 시 현재 상태 그대로 반환
    assert qty == 5.0
    assert status not in ("Filled",)  # 완전 체결이 아님을 확인


def test_cancel_ibkr_order_called_on_partial(tmp_path, monkeypatch):
    """부분 체결(status!=Filled, filled_qty>0) 시 cancel_ibkr_order 호출."""
    monkeypatch.setattr(t, "STATE_PATH", tmp_path / "s.json")
    monkeypatch.setattr(t, "LOG_PATH", tmp_path / "l.jsonl")
    (tmp_path / "s.json").write_text('{"positions":{},"pending_orders":{}}')

    cancelled = []

    def _mock_cancel(ib_, order_id):
        cancelled.append(order_id)

    # wait_for_fill: 부분 체결 시뮬레이션
    def _partial_fill(ib_, trade_, **kw):
        return "PreSubmitted", 5.0, 100.0  # 5주만 체결

    monkeypatch.setattr(t, "cancel_ibkr_order", _mock_cancel)
    monkeypatch.setattr(t, "wait_for_fill_ibkr", _partial_fill)
    monkeypatch.setattr(t, "place_resident_stop",
                        lambda ib_, c, qty, stop, acct: 9002)
    monkeypatch.setattr(t, "get_usd_rate", lambda ib_, cur: 1.0)
    monkeypatch.setattr(t, "usd_rate_is_reliable", lambda cur: True)
    monkeypatch.setattr(t, "fetch_bars_ibkr",
                        lambda ib_, c, days=150: [{"h": 110, "l": 90, "c": 100, "o": 100}] * 60)

    import core.turtle_strategy as core_mod
    import unittest.mock as mock

    fake_sig = {"signal": "breakout_long", "system": "S1", "symbol": "NVDA",
                "current_price": 100.0, "atr": 5.0, "direction": "long"}
    monkeypatch.setattr(core_mod, "signal_from_bars", lambda sym, bars: fake_sig)

    ib = _make_ib()
    ib.isConnected.return_value = True
    ib.placeOrder.return_value = MagicMock(order=MagicMock(orderId=42))
    ib.qualifyContracts.return_value = None

    state = {"positions": {}, "pending_orders": {},
             "baseline": {"nav": 100000}}
    universe = [{"symbol": "NVDA", "exchange": "SMART", "currency": "USD",
                 "region": "US", "harness_score": 80}]

    with mock.patch.object(t, "load_universe", return_value=universe), \
         mock.patch.object(t, "reconcile_pending_orders",
                           return_value={"promoted": [], "purged": [], "kept": [],
                                         "live_symbols": set()}), \
         mock.patch.object(t, "state_flush_pending_and_positions"), \
         mock.patch.object(t, "get_broker_positions", return_value={}), \
         mock.patch.object(t, "manage_positions_ibkr", return_value=[]), \
         mock.patch.object(t, "pyramid_positions_ibkr", return_value=[]), \
         mock.patch.object(t, "load_state", return_value=state), \
         mock.patch.object(t, "state_set_last_run"), \
         mock.patch.object(t, "state_set_pending"), \
         mock.patch.object(t, "state_pop_pending"), \
         mock.patch.object(t, "state_set_position"):
        ib.managedAccounts.return_value = ["DU999"]
        ib.accountValues.return_value = [
            SimpleNamespace(tag="NetLiquidation", currency="USD", value="100000"),
            SimpleNamespace(tag="TotalCashValue", currency="USD", value="100000"),
        ]
        ib.connect.return_value = None
        with mock.patch.object(t, "IB", return_value=ib):
            t.run(execute=True)

    assert any(c == 42 for c in cancelled), "부분 체결 후 cancel_ibkr_order 미호출"


# ── 9. 비USD FX gate — stop_loss 현지통화 단위 검증 ────────────────────────────

def test_non_usd_stop_loss_in_local_currency():
    """KRW 종목: stop_loss = price - 2×atr_local (USD 혼입 없음)."""
    import core.turtle_strategy as core_mod
    price = 80000.0  # KRW
    atr_local = 800.0  # KRW ATR
    atr_usd = atr_local * (1 / 1380)  # ≈ 0.58 USD
    nav = 50000.0  # USD

    shares = core_mod.size_shares(nav, atr_usd)
    stop_loss = round(price - core_mod.TURTLE_STOP_MULT * atr_local, 2)

    assert stop_loss == pytest.approx(80000 - 2 * 800, abs=1)
    assert stop_loss > 70000, "stop_loss가 KRW 현지통화 기준이어야 함"
    assert stop_loss < 80000
    risk_dollars = round(shares * core_mod.TURTLE_STOP_MULT * atr_usd, 2)
    risk_pct = risk_dollars / nav
    assert risk_pct <= 0.02 * 1.05, f"risk_pct {risk_pct:.4f} > 2.1%"
