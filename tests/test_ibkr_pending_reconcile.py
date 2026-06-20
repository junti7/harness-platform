"""IBKR paper trader 의 주문 생명주기 정합(reconcile) 회귀 가드.

배경(2026-06-20, ontology red team §3#2): pending_orders 가 체결/취소 후 정합되지 않아
① 체결돼도 pending 에 남아 exit 모니터(positions 만 스캔)가 손절/청산을 못 걸고,
② 취소/거절은 orphan 으로 남아 재진입을 영구 차단·대시보드 오표시했다.
reconcile_pending_orders 가 브로커 실상태로 promote/keep/purge 한다(주문 side effect 없음).
"""

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_pt():
    name = "pt_for_reconcile_tests"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "ibkr_tws_paper_trader.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class _Con:
    def __init__(self, symbol):
        self.symbol = symbol


class _Pos:
    def __init__(self, symbol, qty):
        self.contract = _Con(symbol)
        self.position = qty


class _Order:
    def __init__(self, oid):
        self.orderId = oid


class _Status:
    def __init__(self, status):
        self.status = status


class _Trade:
    def __init__(self, symbol, oid, status):
        self.contract = _Con(symbol)
        self.order = _Order(oid)
        self.orderStatus = _Status(status)


class _FakeIB:
    def __init__(self, positions, open_trades):
        self._positions = positions
        self._open_trades = open_trades
        self.req_all_called = False

    def positions(self, account=None):
        return self._positions

    def reqAllOpenOrders(self):
        self.req_all_called = True
        return []

    def sleep(self, _s):
        pass

    def openTrades(self):
        return self._open_trades


def _meta(symbol, oid, status="PreSubmitted", qty=10):
    return {
        "entry_ts": "2026-06-19T00:00:00+00:00", "entry_price": 100.0, "atr": 3.0,
        "stop_loss": 94.0, "qty": qty, "exchange": "SMART", "currency": "USD",
        "region": "US", "order_id": oid, "status": status,
    }


class ReconcileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pt = _load_pt()
        cls.pt.log_entry = lambda *a, **k: None  # 테스트 중 실제 로그파일 쓰기 방지

    def test_filled_promoted_to_positions(self):
        state = {"positions": {}, "pending_orders": {"TSM": _meta("TSM", 80, qty=10)}}
        ib = _FakeIB(positions=[_Pos("TSM", 12)], open_trades=[])
        r = self.pt.reconcile_pending_orders(ib, state, "DUX")
        self.assertEqual(r["promoted"], ["TSM"])
        self.assertNotIn("TSM", state["pending_orders"])  # pending 에서 제거
        self.assertIn("TSM", state["positions"])           # positions 로 승격
        self.assertEqual(state["positions"]["TSM"]["status"], "Filled")
        self.assertEqual(state["positions"]["TSM"]["qty"], 12)  # 실제 체결 수량 반영
        # Turtle 파라미터(손절/진입)는 진입 시 값 유지
        self.assertEqual(state["positions"]["TSM"]["stop_loss"], 94.0)

    def test_live_order_kept(self):
        state = {"positions": {}, "pending_orders": {"MU": _meta("MU", 91, status="PreSubmitted")}}
        ib = _FakeIB(positions=[], open_trades=[_Trade("MU", 91, "Submitted")])
        r = self.pt.reconcile_pending_orders(ib, state, "DUX")
        self.assertEqual(r["kept"], ["MU"])
        self.assertIn("MU", state["pending_orders"])
        self.assertEqual(state["pending_orders"]["MU"]["status"], "Submitted")  # status 갱신
        self.assertIn("MU", r["live_symbols"])

    def test_stale_order_purged(self):
        """포지션도 아니고 live order 도 아니면(취소/거절/만료) purge."""
        state = {"positions": {}, "pending_orders": {"NVDA": _meta("NVDA", 7)}}
        ib = _FakeIB(positions=[], open_trades=[])
        r = self.pt.reconcile_pending_orders(ib, state, "DUX")
        self.assertEqual(r["purged"], ["NVDA"])
        self.assertNotIn("NVDA", state["pending_orders"])

    def test_corrupt_meta_purged(self):
        state = {"positions": {}, "pending_orders": {"BAD": ["not", "a", "dict"]}}
        ib = _FakeIB(positions=[], open_trades=[])
        r = self.pt.reconcile_pending_orders(ib, state, "DUX")
        self.assertEqual(r["purged"], ["BAD"])
        self.assertNotIn("BAD", state["pending_orders"])

    def test_empty_noop(self):
        state = {"positions": {}, "pending_orders": {}}
        ib = _FakeIB(positions=[], open_trades=[])
        r = self.pt.reconcile_pending_orders(ib, state, "DUX")
        self.assertEqual((r["promoted"], r["kept"], r["purged"]), ([], [], []))

    def test_mixed_batch(self):
        state = {"positions": {}, "pending_orders": {
            "TSM": _meta("TSM", 80), "MU": _meta("MU", 91), "NVDA": _meta("NVDA", 7),
        }}
        ib = _FakeIB(positions=[_Pos("TSM", 10)], open_trades=[_Trade("MU", 91, "PreSubmitted")])
        r = self.pt.reconcile_pending_orders(ib, state, "DUX")
        self.assertEqual(r["promoted"], ["TSM"])
        self.assertEqual(r["kept"], ["MU"])
        self.assertEqual(r["purged"], ["NVDA"])
        self.assertEqual(set(state["pending_orders"].keys()), {"MU"})
        self.assertIn("TSM", state["positions"])


if __name__ == "__main__":
    unittest.main()
