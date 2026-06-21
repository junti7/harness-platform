"""core.atomic_io.atomic_write_json 회귀 가드(torn-file 방지).

배경(2026-06-20, Red Team): IBKR 상태 파일을 monitor/trader/backend 가 교차로 읽고 쓴다.
비원자적 write 는 동시 read 시 잘린 JSON 을 노출할 수 있어, tmp→fsync→os.replace 로 교체한다.
"""

import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path

from core.atomic_io import atomic_write_json, update_json_atomic


class _Unserializable:
    pass


class UpdateJsonAtomicTests(unittest.TestCase):
    """update_json_atomic = 락 + 디스크 최신본 재독 + 델타 병합 (2026-06-21 multi-writer race 수정)."""

    def test_delta_merge_no_clobber(self):
        """트레이더(pending→positions 승격)와 모니터(nav_history)가 서로를 안 덮어쓴다 — race 시나리오."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ibkr_tws_positions.json"
            p.write_text(json.dumps({"positions": {}, "pending_orders": {"TSM": {"status": "PreSubmitted"}}, "nav_history": []}))

            # 트레이더 델타: TSM pending→positions 승격, pending 비움(트레이더 소유)
            def trader(fresh):
                fresh["positions"]["TSM"] = {"status": "Filled", "qty": 10}
                fresh["pending_orders"] = {}

            # 모니터 델타: nav_history 만 갱신, pending/positions 통째 대입 안 함(소유 외)
            def monitor(fresh):
                fresh.setdefault("nav_history", []).append({"date": "06/21", "value": 1000})

            # 순서 무관하게 둘 다 반영돼야(락 직렬화 + fresh 재독 + 델타)
            update_json_atomic(p, monitor)   # 모니터가 먼저(트레이더 승격 전 stale view 흉내)
            update_json_atomic(p, trader)
            r = json.loads(p.read_text())
            self.assertIn("TSM", r["positions"])          # 트레이더 승격 보존
            self.assertNotIn("TSM", r["pending_orders"])  # 트레이더가 비운 pending 보존
            self.assertEqual(len(r["nav_history"]), 1)    # 모니터 변경 보존(클로버 안 됨)

    def test_monitor_never_clobbers_pending(self):
        """모니터 델타(nav만)는 트레이더 소유 pending_orders 를 절대 건드리지 않는다."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text(json.dumps({"positions": {}, "pending_orders": {"MU": {"status": "Submitted"}}}))
            update_json_atomic(p, lambda fresh: fresh.update({"nav_history": [1]}))
            r = json.loads(p.read_text())
            self.assertEqual(r["pending_orders"], {"MU": {"status": "Submitted"}})

    def test_lock_serializes_no_lost_updates(self):
        """진짜 동시성(스레드 20개 increment)에서 락이 lost-update 를 막는다(최종==20)."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "counter.json"
            p.write_text(json.dumps({"n": 0}))

            def inc():
                update_json_atomic(p, lambda fresh: fresh.update({"n": int(fresh.get("n", 0)) + 1}))

            threads = [threading.Thread(target=inc) for _ in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(json.loads(p.read_text())["n"], 20)

    def test_corrupt_disk_state_starts_empty(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text("not json{{{")
            update_json_atomic(p, lambda fresh: fresh.update({"ok": True}))
            self.assertEqual(json.loads(p.read_text()), {"ok": True})


class AtomicWriteJsonTests(unittest.TestCase):
    def test_write_and_no_tmp_residue(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "state.json"
            atomic_write_json(target, {"a": 1, "ts": "x"})
            self.assertEqual(json.loads(target.read_text()), {"a": 1, "ts": "x"})
            self.assertEqual(list(Path(d).glob(".state.json.*.tmp")), [])

    def test_atomic_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "state.json"
            atomic_write_json(target, {"a": 1})
            atomic_write_json(target, {"a": 2})
            self.assertEqual(json.loads(target.read_text()), {"a": 2})

    def test_failure_preserves_existing_and_cleans_tmp(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "state.json"
            atomic_write_json(target, {"a": 2})
            with self.assertRaises(Exception):
                atomic_write_json(target, {"bad": _Unserializable()})
            self.assertEqual(json.loads(target.read_text()), {"a": 2})  # 기존 보존
            self.assertEqual(list(Path(d).glob(".state.json.*.tmp")), [])  # tmp 누수 없음

    def test_existing_mode_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "state.json"
            target.write_text("{}", encoding="utf-8")
            os.chmod(target, 0o640)
            atomic_write_json(target, {"a": 1})
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)


if __name__ == "__main__":
    unittest.main()
