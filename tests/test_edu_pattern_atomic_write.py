"""edu 패턴 모니터 스크립트의 원자적 쓰기 회귀 가드.

배경(2026-06-17): backend `_run_edu_pattern_pipeline` 가 build/fact_check 스크립트를
timeout=90 subprocess 로 돌리는데, 두 스크립트가 OUTPUT_PATH.write_text 로 *비원자적*
기록하면 타임아웃 SIGKILL 이 쓰기 도중 들어올 때 잘린 JSON(torn-file)이 남아 프론트가
빈 화면으로 떨어질 수 있었다. _atomic_write_json(tmp→fsync→os.replace)으로 교체.

가드 포인트:
  1. 정상 쓰기: 유효 JSON 이 기록되고, 디렉터리에 `.tmp` 잔여물이 없다.
  2. 덮어쓰기: 기존 내용을 새 내용으로 원자 교체.
  3. 쓰기 실패(직렬화 불가): 예외를 올리고 *기존 파일을 손상시키지 않으며* tmp 를 정리한다.
"""

import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


def _load_script_module(filename: str, modname: str):
    path = Path(__file__).resolve().parents[1] / "scripts" / filename
    spec = importlib.util.spec_from_file_location(modname, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _Unserializable:
    pass


class AtomicWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = _load_script_module("build_edu_pattern_intelligence.py", "edu_build_for_tests")
        cls.fc = _load_script_module("fact_check_edu_patterns.py", "edu_fc_for_tests")

    def _check_module(self, mod):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "out.json"

            # 1. 정상 쓰기 + tmp 잔여물 없음
            mod._atomic_write_json(target, {"a": 1, "ts": "x"})
            self.assertEqual(json.loads(target.read_text()), {"a": 1, "ts": "x"})
            self.assertEqual(list(Path(d).glob(".out.json.*.tmp")), [])

            # 2. 원자 덮어쓰기
            mod._atomic_write_json(target, {"a": 2})
            self.assertEqual(json.loads(target.read_text()), {"a": 2})

            # 3. 직렬화 불가 → 예외, 기존 파일 보존, tmp 정리
            with self.assertRaises(Exception):
                mod._atomic_write_json(target, {"bad": _Unserializable()})
            self.assertEqual(json.loads(target.read_text()), {"a": 2})  # 기존 보존
            self.assertEqual(list(Path(d).glob(".out.json.*.tmp")), [])  # tmp 누수 없음

    def _check_mode_preserved(self, mod):
        """신규 파일은 제한적 0600(권한 확대 없음), 기존 파일은 mode 승계(Codex r3/r4/r5)."""
        with tempfile.TemporaryDirectory() as d:
            # 신규 파일: mkstemp 기본 0600 (write_text 0644 보다 제한적 — 권한 확대 없음, 동일 사용자 read 가능)
            new_target = Path(d) / "new.json"
            mod._atomic_write_json(new_target, {"a": 1})
            self.assertEqual(stat.S_IMODE(new_target.stat().st_mode), 0o600)

            # 기존 파일 모드 승계: 0640 으로 만들어 두고 덮어써도 0640 유지(copystat)
            target = Path(d) / "existing.json"
            target.write_text("{}", encoding="utf-8")
            os.chmod(target, 0o640)
            mod._atomic_write_json(target, {"a": 2})
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)

    def test_new_file_mode_independent_of_umask(self):
        """신규 파일은 umask 와 무관하게 0600 (전역 umask 조작 없음, 권한 확대 불가) — Codex r5."""
        old = os.umask(0o000)  # 가장 느슨한 umask 에서도
        try:
            with tempfile.TemporaryDirectory() as d:
                target = Path(d) / "loose.json"
                self.build._atomic_write_json(target, {"a": 1})
                self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        finally:
            os.umask(old)

    def test_build_atomic_write(self):
        self._check_module(self.build)

    def test_fact_check_atomic_write(self):
        self._check_module(self.fc)

    def test_build_mode_preserved(self):
        self._check_mode_preserved(self.build)

    def test_fact_check_mode_preserved(self):
        self._check_mode_preserved(self.fc)


if __name__ == "__main__":
    unittest.main()
