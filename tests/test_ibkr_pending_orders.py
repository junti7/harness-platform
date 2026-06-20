"""IBKR 모니터의 대기 주문(미체결) 가시화 회귀 가드.

배경(2026-06-20, handoff ibkr_pending_visibility):
  ibkr_tws_paper_trader 가 진입 주문을 placeOrder 후 미체결이면 state["pending_orders"][sym]
  에 durable 하게 적재한다. 그러나 ibkr_turtle_monitor.run() 은 state["positions"] 만 순회해
  PreSubmitted/PendingSubmit 진입 주문(TSM/MU/SK하이닉스)이 모니터 JSON·대시보드에서 사라졌다.
  assess_pending_order / _collect_pending_orders 로 이를 화면용으로 노출한다.

가드 포인트:
  1. assess_pending_order 가 현재가 대비 진입기준 갭과 경과시간을 계산한다.
  2. 후보 가격이 없으면 current_price/gap 은 None(부작용 없는 읽기 전용).
  3. _collect_pending_orders 가 state["pending_orders"] 전부를 리스트로 반환한다.
  4. naive entry_ts 도 UTC 로 간주해 age_hours 를 계산(crash 없이).
"""

import importlib.util
import sys
import unittest
from pathlib import Path


def _load_monitor():
    module_name = "ibkr_turtle_monitor_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "ibkr_turtle_monitor.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_META = {
    "symbol": "TSM", "entry_price": 100.0, "qty": 10, "exchange": "NYSE",
    "currency": "USD", "region": "US", "stop_loss": 90.0, "atr": 3.0,
    "order_id": 42, "status": "PreSubmitted", "entry_ts": "2026-06-19T00:00:00+00:00",
}


class PendingOrderAssessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = _load_monitor()

    def test_gap_and_status_with_candidate(self):
        r = self.m.assess_pending_order(_META, {"symbol": "TSM", "current_price": 105.0})
        self.assertEqual(r["gap_to_entry_pct"], 5.0)
        self.assertEqual(r["status"], "PreSubmitted")
        self.assertEqual(r["current_price"], 105.0)
        self.assertIsNotNone(r["age_hours"])

    def test_no_candidate_price_none(self):
        r = self.m.assess_pending_order(_META, None)
        self.assertIsNone(r["current_price"])
        self.assertIsNone(r["gap_to_entry_pct"])

    def test_naive_entry_ts_does_not_crash(self):
        meta = {**_META, "entry_ts": "2026-06-19T00:00:00"}  # tz 없음
        r = self.m.assess_pending_order(meta, None)
        self.assertIsNotNone(r["age_hours"])

    def test_missing_status_defaults_pending(self):
        meta = {**_META}; meta.pop("status")
        self.assertEqual(self.m.assess_pending_order(meta, None)["status"], "pending")

    def test_collect_from_state(self):
        state = {"pending_orders": {"TSM": _META, "MU": {**_META, "symbol": "MU"}}}
        cands = [{"symbol": "TSM", "current_price": 105.0}]
        res = self.m._collect_pending_orders(state, cands, json_mode=True)
        self.assertEqual(len(res), 2)
        by = {r["symbol"]: r for r in res}
        self.assertEqual(by["TSM"]["current_price"], 105.0)
        self.assertIsNone(by["MU"]["current_price"])  # 스캔에 없으면 None

    def test_collect_empty_state(self):
        self.assertEqual(self.m._collect_pending_orders({}, [], json_mode=True), [])
        self.assertEqual(
            self.m._collect_pending_orders({"pending_orders": {}}, [], json_mode=True), []
        )

    def test_collect_corrupt_shape_does_not_crash(self):
        """state["pending_orders"]가 dict 가 아닌 손상 shape 여도 죽지 않고 [] 강등(Red Team MAJOR)."""
        for bad in ([], "oops", 42, None):
            self.assertEqual(
                self.m._collect_pending_orders({"pending_orders": bad}, [], json_mode=True), []
            )

    def test_run_offline_tolerates_corrupt_pending(self):
        """run_offline 도 손상된 pending_orders 에서 예외 없이 동작(cold-start 관측 안전)."""
        import unittest.mock as _mock
        with _mock.patch.object(self.m, "load_state", return_value={"positions": {}, "pending_orders": ["bad"]}), \
             _mock.patch.object(self.m, "load_universe", return_value=([], "test")), \
             _mock.patch.object(self.m, "_read_ibkr_order_history", return_value=([], True)):
            out = self.m.run_offline()
        self.assertEqual(out["pending_orders"], [])
        self.assertIn("ok", out)

    def test_load_state_coerces_corrupt_shapes(self):
        """load_state 가 손상된 positions/pending_orders(non-dict)를 빈 dict 로 교정(Red Team r3 MAJOR)."""
        import json as _json
        import tempfile as _tf
        from pathlib import Path as _P
        with _tf.TemporaryDirectory() as d:
            p = _P(d) / "state.json"
            p.write_text(_json.dumps({"positions": ["corrupt"], "pending_orders": "bad", "last_run": "x"}))
            import unittest.mock as _mock
            with _mock.patch.object(self.m, "STATE_PATH", p):
                st = self.m.load_state()
            self.assertEqual(st["positions"], {})
            self.assertEqual(st["pending_orders"], {})
            self.assertEqual(st["last_run"], "x")  # 정상 필드는 보존

    def test_load_state_non_dict_root_becomes_empty(self):
        """state 루트가 dict 가 아니면(list 등) 빈 dict 로 강등."""
        import json as _json, tempfile as _tf, unittest.mock as _mock
        from pathlib import Path as _P
        with _tf.TemporaryDirectory() as d:
            p = _P(d) / "state.json"
            p.write_text(_json.dumps(["not", "a", "dict"]))
            with _mock.patch.object(self.m, "STATE_PATH", p):
                st = self.m.load_state()
            self.assertIsInstance(st, dict)


if __name__ == "__main__":
    unittest.main()
