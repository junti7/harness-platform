"""core.atomic_io.atomic_write_json 회귀 가드(torn-file 방지).

배경(2026-06-20, Red Team): IBKR 상태 파일을 monitor/trader/backend 가 교차로 읽고 쓴다.
비원자적 write 는 동시 read 시 잘린 JSON 을 노출할 수 있어, tmp→fsync→os.replace 로 교체한다.
"""

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from core.atomic_io import atomic_write_json


class _Unserializable:
    pass


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
