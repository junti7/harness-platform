"""IBKR 모니터 캐시 파싱/쓰기 회귀 가드.

배경(2026-06-17 버그): IBKR 포트폴리오 추이 차트가 06/12에 멈춤.
근본 원인 — backend 백그라운드 갱신이 `json.loads(stdout 전체)` 로 캐시를 썼는데,
import 시점에 core.trading_universe 의 Ollama 번역 진행 로그가 stdout 앞부분을
오염시켜 첫 글자에서 파싱이 깨졌다("Expecting value: line 1 column 1").
스크립트는 --json 모드에서 *마지막 한 줄*로만 결과 JSON을 낸다.

가드 포인트(Red Team Codex 2026-06-17 2라운드 반영):
  1. stdout 선행/후행에 비-JSON 잡음이 섞여도 결과 JSON 줄을 찾아낸다.
  2. 모니터 결과 스키마를 만족하는 객체만 채택 → stray {"ok":...} 디버그 JSON 오발행 방지.
  3. 결과 JSON 줄이 없거나 rc!=0/빈 stdout 이면 캐시를 보존하고 에러로그에 단서를 남긴다.
  4. 캐시 쓰기는 원자적(tmp+rename)이라 중간 실패 시 빈/잘린 파일을 남기지 않는다.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def _load_backend_main():
    module_name = "harness_backend_main_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "harness-os" / "backend" / "main.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeCompleted:
    def __init__(self, stdout, returncode=0, stderr=""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def _result(ts="2026-06-17T06:02:02+00:00", nav_history=None, mode="paper"):
    """모니터 결과 스키마(_is_ibkr_monitor_result)를 만족하는 최소 결과 dict."""
    return {
        "ok": True,
        "ts": ts,
        "mode": mode,
        "gateway_connected": True,
        "account": {"nav": 1010677.46},
        "positions": [],
        "entry_candidates": [],
        "nav_history": nav_history if nav_history is not None
        else [{"date": "06/17", "value": 1010677.46, "pnl_pct": -1.462}],
    }


class IbkrResultJsonExtractTests(unittest.TestCase):
    """순수 파서 단위 테스트 — 선행/후행 오염 내성 + 스키마 검증."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def _extract(self, stdout):
        return self.mod._extract_ibkr_result_json(stdout, json)

    def test_leading_noise(self):
        noise = "\n".join(["Local LLM (Ollama) translated chunk (3 items)."] * 9)
        stdout = noise + "\n" + json.dumps(_result(), ensure_ascii=False) + "\n"
        got = self._extract(stdout)
        self.assertIsNotNone(got)
        self.assertEqual(got["nav_history"][-1]["date"], "06/17")

    def test_trailing_noise(self):
        """결과 JSON 뒤에 추가 stdout 줄이 붙어도 결과를 찾는다(Codex 1R BLOCKER)."""
        stdout = (
            "leading noise\n"
            + json.dumps(_result(), ensure_ascii=False) + "\n"
            + "Local LLM (Ollama) completed translations for 5 items.\n"
            + "some trailing line\n"
        )
        got = self._extract(stdout)
        self.assertIsNotNone(got)
        self.assertEqual(got["nav_history"][-1]["date"], "06/17")

    def test_clean(self):
        got = self._extract(json.dumps(_result()) + "\n")
        self.assertIsNotNone(got)
        self.assertTrue(got["ok"])

    def test_no_result_line(self):
        self.assertIsNone(self._extract("noise only\nmore noise\n"))

    def test_stray_ok_json_rejected(self):
        """ok 키만 있는 stray 디버그 JSON 은 모니터 결과로 채택하지 않는다(Codex 2R MAJOR)."""
        self.assertIsNone(self._extract('{"ok": true}\n'))
        self.assertIsNone(self._extract('{"ok": true, "message": "done"}\n'))

    def test_wrong_typed_json_rejected(self):
        """키는 맞지만 타입이 깨진 JSON 은 채택하지 않는다(Codex 3R MAJOR).

        {"positions": "oops", "gateway_connected": "yes"} 처럼 키만 맞으면
        이전 구현은 통과시켰다. 타입 검증으로 거른다.
        """
        bad = {"ok": True, "ts": "x", "gateway_connected": "yes",
               "positions": "oops", "entry_candidates": {}}
        self.assertIsNone(self._extract(json.dumps(bad) + "\n"))
        # ts 가 빈 문자열인 경우도 거부
        bad2 = {"ok": True, "ts": "", "gateway_connected": True,
                "positions": [], "entry_candidates": []}
        self.assertIsNone(self._extract(json.dumps(bad2) + "\n"))

    def test_trailing_stray_ok_json_does_not_shadow_real_result(self):
        """결과 JSON 뒤에 stray {"ok":...} 가 붙어도 진짜 결과를 채택한다."""
        stdout = (
            json.dumps(_result(), ensure_ascii=False) + "\n"
            + '{"ok": true, "message": "done"}\n'
        )
        got = self._extract(stdout)
        self.assertIsNotNone(got)
        self.assertEqual(got["nav_history"][-1]["date"], "06/17")

    def test_picks_last_valid_result_when_multiple(self):
        old = json.dumps(_result(ts="2026-06-17T09:00:00+00:00", nav_history=[]))
        new = json.dumps(_result(ts="2026-06-17T10:00:00+00:00", nav_history=[]))
        got = self._extract(old + "\n" + new + "\n")
        self.assertEqual(got["ts"], "2026-06-17T10:00:00+00:00")

    def test_non_iso_ts_rejected(self):
        """ts 가 ISO8601 로 파싱 불가하면 거부(비-ISO 고착 방지, Codex 6R BLOCKER)."""
        self.assertIsNone(self._extract(json.dumps(_result(ts="z")) + "\n"))
        self.assertIsNone(self._extract(json.dumps(_result(ts="not-a-date")) + "\n"))

    def test_naive_and_dateonly_ts_rejected(self):
        """tz-naive / date-only ts 는 거부(aware↔naive 비교 무력화 방지, Codex 7R BLOCKER)."""
        self.assertIsNone(self._extract(json.dumps(_result(ts="2026-06-17T11:00:00")) + "\n"))  # naive
        self.assertIsNone(self._extract(json.dumps(_result(ts="2026-06-17")) + "\n"))  # date-only
        # 'Z' 접미 UTC 는 aware 로 허용
        self.assertIsNotNone(self._extract(json.dumps(_result(ts="2026-06-17T11:00:00Z")) + "\n"))

    def test_broken_nav_history_rejected(self):
        """nav_history 가 있는데 list/dict shape 가 아니면 거부(차트 경로 보호, Codex 6R BLOCKER)."""
        bad = _result()
        bad["nav_history"] = "broken"
        self.assertIsNone(self._extract(json.dumps(bad) + "\n"))
        bad2 = _result()
        bad2["nav_history"] = ["not-a-dict"]
        self.assertIsNone(self._extract(json.dumps(bad2) + "\n"))

    def test_missing_nav_history_allowed(self):
        """offline/exception 결과처럼 nav_history 가 없으면 허용(필수 아님)."""
        offline = _result()
        del offline["nav_history"]
        self.assertIsNotNone(self._extract(json.dumps(offline) + "\n"))

    def test_missing_mode_rejected(self):
        """mode 누락 결과는 거부(자본 UI 가 paper 로 오표시되는 것 방지, Codex 8R BLOCKER)."""
        no_mode = _result()
        del no_mode["mode"]
        self.assertIsNone(self._extract(json.dumps(no_mode) + "\n"))
        # mode 가 빈 문자열/비-str 도 거부
        self.assertIsNone(self._extract(json.dumps(_result(mode="")) + "\n"))

    def test_mode_enum_enforced(self):
        """mode 는 {"paper","live"} 정확히만 허용(9R BLOCKER): "prod"/"live "/"PAPER" 거부."""
        for bad in ("prod", "live ", "PAPER", "paper-ish", "demo"):
            self.assertIsNone(self._extract(json.dumps(_result(mode=bad)) + "\n"), bad)
        self.assertIsNotNone(self._extract(json.dumps(_result(mode="live")) + "\n"))
        self.assertIsNotNone(self._extract(json.dumps(_result(mode="paper")) + "\n"))

    def test_broken_nav_point_fields_rejected(self):
        """nav_history 원소가 NavPoint 필드 계약을 어기면 거부(9R MAJOR)."""
        for bad_nav in ([{}], [{"date": 1, "value": "x"}], [{"date": "06/17", "value": "nope"}],
                        [{"date": "06/17", "value": True}], [{"value": 1.0}]):
            self.assertIsNone(self._extract(json.dumps(_result(nav_history=bad_nav)) + "\n"), bad_nav)
        # 정상 NavPoint(및 pnl_pct null) 는 허용
        self.assertIsNotNone(self._extract(json.dumps(_result(
            nav_history=[{"date": "06/17", "value": 1.5, "pnl_pct": None}])) + "\n"))

    def test_nan_inf_nav_value_rejected(self):
        """NaN/Infinity nav 값은 거부(외부 입력 신뢰 경계, Codex 10R MINOR)."""
        for bad in ("NaN", "Infinity", "-Infinity"):
            line = '{"ok": true, "ts": "2026-06-17T06:02:02+00:00", "mode": "paper", "gateway_connected": true, "account": null, "positions": [], "entry_candidates": [], "nav_history": [{"date": "06/17", "value": ' + bad + '}]}'
            self.assertIsNone(self._extract(line + "\n"), bad)

    def test_wrong_shape_optional_containers_rejected(self):
        """프론트가 순회하는 exit_signals/recent_orders(array)·forex_rates(object) wrong-shape 거부(11R MAJOR)."""
        bad_es = _result(); bad_es["exit_signals"] = {}
        self.assertIsNone(self._extract(json.dumps(bad_es) + "\n"))
        bad_ro = _result(); bad_ro["recent_orders"] = {}
        self.assertIsNone(self._extract(json.dumps(bad_ro) + "\n"))
        bad_fx = _result(); bad_fx["forex_rates"] = []
        self.assertIsNone(self._extract(json.dumps(bad_fx) + "\n"))
        # 올바른 타입(또는 미존재)은 허용
        ok = _result(); ok["exit_signals"] = ["AAA"]; ok["recent_orders"] = []; ok["forex_rates"] = {"USD": 1}
        self.assertIsNotNone(self._extract(json.dumps(ok) + "\n"))

    def test_exception_fallback_shape_accepted(self):
        """monitor 의 top-level exception fallback shape(ok=False·mode 있음·nav_history 없음)은 유효."""
        fallback = {
            "ok": False, "ts": "2026-06-17T06:02:02+00:00", "mode": "paper",
            "gateway_connected": False, "account": None, "positions": [],
            "exit_signals": [], "entry_candidates": [], "universe_source": "hardcoded",
            "recent_orders": [], "orders_history_ok": False, "error": "boom",
        }
        self.assertIsNotNone(self._extract(json.dumps(fallback) + "\n"))


class IbkrCacheWriteTests(unittest.TestCase):
    """_run_ibkr_monitor_background 의 캐시 쓰기/보존 동작."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def _run(self, stdout, returncode=0, preexisting=None):
        mod = self.mod
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "ibkr_monitor_cache.json"
            errlog = Path(d) / "logs" / "backend.error.log"
            if preexisting is not None:
                cache.write_text(json.dumps(preexisting), encoding="utf-8")
            completed = _FakeCompleted(stdout, returncode)
            # subprocess.run·캐시 경로·에러로그 경로 모두 컨텍스트 패치로 격리(워크스페이스 오염·병렬 충돌 방지).
            with mock.patch("subprocess.run", return_value=completed), \
                 mock.patch.object(mod, "_IBKR_CACHE_PATH", cache), \
                 mock.patch.object(mod, "_IBKR_ERROR_LOG_PATH", errlog):
                mod._run_ibkr_monitor_background()
            written = json.loads(cache.read_text()) if cache.exists() else None
            logged = errlog.read_text() if errlog.exists() else ""
            return written, logged

    def test_polluted_stdout_writes_cache(self):
        noise = "\n".join(["Local LLM (Ollama) translated chunk (3 items)."] * 9)
        stdout = noise + "\n" + json.dumps(_result(), ensure_ascii=False) + "\n"
        written, _ = self._run(stdout)
        self.assertIsNotNone(written)
        self.assertEqual(written["nav_history"][-1]["date"], "06/17")

    def test_no_json_preserves_existing_cache_and_logs(self):
        """결과 줄이 없으면 기존 캐시를 보존하고 에러로그에 단서를 남긴다."""
        prior = {"ok": True, "ts": "prior", "nav_history": [{"date": "06/12", "value": 1.0}]}
        written, logged = self._run("noise only\nmore noise\n", preexisting=prior)
        self.assertEqual(written, prior)
        self.assertIn("background scan failed", logged)

    def test_nonzero_returncode_preserves_existing_cache_and_logs(self):
        prior = {"ok": True, "ts": "prior"}
        written, logged = self._run(json.dumps(_result()), returncode=1, preexisting=prior)
        self.assertEqual(written, prior)
        self.assertIn("rc=1", logged)

    def test_empty_stdout_logs_breadcrumb(self):
        """rc=0 인데 stdout 이 비면 silent no-op 이 아니라 명시 에러로그를 남긴다(Codex 2R MINOR)."""
        written, logged = self._run("   \n", returncode=0)
        self.assertIsNone(written)
        self.assertIn("stdout_empty=True", logged)

    def test_write_fault_preserves_existing_cache(self):
        """os.replace 가 실패해도(원자적 쓰기 중단) 기존 캐시가 보존되고 tmp 가 정리된다(Codex 3R MINOR)."""
        import os as _os
        mod = self.mod
        prior = {"ok": True, "ts": "prior", "nav_history": [{"date": "06/12", "value": 1.0}]}
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "ibkr_monitor_cache.json"
            errlog = Path(d) / "logs" / "backend.error.log"
            cache.write_text(json.dumps(prior), encoding="utf-8")
            completed = _FakeCompleted(json.dumps(_result()), 0)
            real_replace = _os.replace

            def boom(src, dst):
                raise OSError("disk full")

            with mock.patch("subprocess.run", return_value=completed), \
                 mock.patch.object(mod, "_IBKR_CACHE_PATH", cache), \
                 mock.patch.object(mod, "_IBKR_ERROR_LOG_PATH", errlog), \
                 mock.patch("os.replace", side_effect=boom):
                mod._run_ibkr_monitor_background()
            # 기존 캐시 그대로 보존
            self.assertEqual(json.loads(cache.read_text()), prior)
            # tmp 잔여물 없음(.ibkr_cache_*.tmp)
            leftovers = list(Path(d).glob(".ibkr_cache_*.tmp"))
            self.assertEqual(leftovers, [], f"tmp 잔여물 발견: {leftovers}")
            self.assertIn("background scan failed", errlog.read_text())


class IbkrCacheWriteOrderingTests(unittest.TestCase):
    """_write_ibkr_cache_atomic 의 ts 단조성(오래된 결과가 새 결과를 덮지 않음, Codex 5R MAJOR)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def test_older_ts_does_not_overwrite_newer(self):
        mod = self.mod
        newer = _result(ts="2026-06-17T10:00:00+00:00", nav_history=[{"date": "06/17", "value": 2.0}])
        older = _result(ts="2026-06-17T09:00:00+00:00", nav_history=[{"date": "06/17", "value": 1.0}])
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "c.json"
            cache.write_text(json.dumps(newer), encoding="utf-8")
            with mock.patch.object(mod, "_IBKR_CACHE_PATH", cache):
                mod._write_ibkr_cache_atomic(older)
            self.assertEqual(json.loads(cache.read_text())["ts"], newer["ts"])  # 최신 보존

    def test_newer_ts_overwrites_older(self):
        mod = self.mod
        older = _result(ts="2026-06-17T09:00:00+00:00")
        newer = _result(ts="2026-06-17T11:00:00+00:00")
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "c.json"
            cache.write_text(json.dumps(older), encoding="utf-8")
            with mock.patch.object(mod, "_IBKR_CACHE_PATH", cache):
                mod._write_ibkr_cache_atomic(newer)
            self.assertEqual(json.loads(cache.read_text())["ts"], newer["ts"])

    def test_writer_rejects_invalid_data(self):
        """canonical safe writer 는 모니터 결과가 아닌 data 를 거부한다(Codex 7R MINOR 자가검증)."""
        mod = self.mod
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "c.json"
            with mock.patch.object(mod, "_IBKR_CACHE_PATH", cache):
                with self.assertRaises(ValueError):
                    mod._write_ibkr_cache_atomic({"ok": True, "positions": "oops"})
            self.assertFalse(cache.exists())

    def test_corrupt_existing_cache_is_overwritten(self):
        """기존 캐시가 깨졌으면 ts 가드를 건너뛰고 새 결과로 복구한다."""
        mod = self.mod
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "c.json"
            cache.write_text("{ broken json", encoding="utf-8")
            with mock.patch.object(mod, "_IBKR_CACHE_PATH", cache):
                mod._write_ibkr_cache_atomic(_result(ts="2026-06-17T11:00:00+00:00"))
            self.assertEqual(json.loads(cache.read_text())["ts"], "2026-06-17T11:00:00+00:00")


class IbkrLoadValidCacheTests(unittest.TestCase):
    """_load_valid_ibkr_cache: GET reader 가 깨진/legacy 캐시를 서비스하지 않는다(Codex 5R MAJOR)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def _load(self, content=None, missing=False):
        mod = self.mod
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "c.json"
            errlog = Path(d) / "logs" / "e.log"
            if not missing:
                cache.write_text(content, encoding="utf-8")
            with mock.patch.object(mod, "_IBKR_CACHE_PATH", cache), \
                 mock.patch.object(mod, "_IBKR_ERROR_LOG_PATH", errlog):
                got = mod._load_valid_ibkr_cache()
                logged = errlog.read_text() if errlog.exists() else ""
            return got, logged

    def test_valid_cache_returned(self):
        got, _ = self._load(json.dumps(_result()))
        self.assertIsNotNone(got)
        self.assertEqual(got["nav_history"][-1]["date"], "06/17")

    def test_missing_returns_none(self):
        got, _ = self._load(missing=True)
        self.assertIsNone(got)

    def test_corrupt_returns_none_and_logs(self):
        got, logged = self._load("{ broken")
        self.assertIsNone(got)
        self.assertIn("읽기 실패", logged)

    def test_wrong_shape_returns_none_and_logs(self):
        """valid JSON 이지만 모니터 결과 스키마가 아니면 서비스 보류."""
        got, logged = self._load(json.dumps({"ok": True, "positions": "oops"}))
        self.assertIsNone(got)
        self.assertIn("스키마 불일치", logged)


class IbkrCacheUploadTests(unittest.TestCase):
    """post_ibkr_cache_upload 가 background writer 와 동일한 안전계약(검증+원자쓰기)을 따르는지(Codex 4R MAJOR)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def test_valid_payload_written_atomically(self):
        mod = self.mod
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "ibkr_monitor_cache.json"
            with mock.patch.object(mod, "_IBKR_CACHE_PATH", cache):
                resp = mod.post_ibkr_cache_upload(payload=_result(), _=None)
            self.assertTrue(resp["ok"])
            self.assertEqual(json.loads(cache.read_text())["nav_history"][-1]["date"], "06/17")

    def test_malformed_payload_rejected_and_cache_preserved(self):
        """타입깨진 업로드 payload 는 400 으로 거부하고 기존 캐시를 보존한다."""
        mod = self.mod
        prior = {"ok": True, "ts": "prior"}
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "ibkr_monitor_cache.json"
            cache.write_text(json.dumps(prior), encoding="utf-8")
            bad = {"ok": True, "ts": "x", "gateway_connected": "yes",
                   "positions": "oops", "entry_candidates": {}}
            with mock.patch.object(mod, "_IBKR_CACHE_PATH", cache):
                with self.assertRaises(mod.HTTPException) as ctx:
                    mod.post_ibkr_cache_upload(payload=bad, _=None)
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(json.loads(cache.read_text()), prior)  # 기존 캐시 보존

    def test_write_failure_raises_500(self):
        """쓰기 실패는 200 {"ok": false} 가 아니라 HTTP 500(Codex 5R MINOR)."""
        mod = self.mod
        with tempfile.TemporaryDirectory() as d:
            cache = Path(d) / "ibkr_monitor_cache.json"
            with mock.patch.object(mod, "_IBKR_CACHE_PATH", cache), \
                 mock.patch.object(mod, "_write_ibkr_cache_atomic", side_effect=OSError("disk full")):
                with self.assertRaises(mod.HTTPException) as ctx:
                    mod.post_ibkr_cache_upload(payload=_result(), _=None)
            self.assertEqual(ctx.exception.status_code, 500)


class IbkrInFlightGuardTests(unittest.TestCase):
    """GET 가 background 스레드 start 에 실패해도 in-flight 플래그가 영구 True 로 안 남는다(Codex 9R MAJOR)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def test_thread_start_failure_resets_inflight(self):
        mod = self.mod
        valid = _result()

        class _BoomThread:
            def __init__(self, *a, **k): pass
            def start(self): raise RuntimeError("can't start new thread")

        sentinel_last_run = 123.0
        mod._IBKR_LAST_RUN = sentinel_last_run   # should_run 은 cache None 으로 유도, LAST_RUN 롤백 확인용
        mod._IBKR_RUN_IN_PROGRESS = False
        with mock.patch.object(mod, "_load_valid_ibkr_cache", return_value=None), \
             mock.patch.object(mod, "_merge_ibkr_gateway_status", side_effect=lambda p: p), \
             mock.patch.object(mod, "_ibkr_log_error", lambda *a, **k: None), \
             mock.patch.object(mod.threading, "Thread", _BoomThread):
            # cache None 이라 offline 분기로 진입; 거기서 예외가 나도 무방(스레드 start 실패 복구만 검증)
            try:
                mod.get_ibkr_monitor(_=None)
            except Exception:
                pass
        self.assertFalse(mod._IBKR_RUN_IN_PROGRESS, "start 실패 후 in-flight 가 False 로 복구돼야 한다")
        self.assertEqual(mod._IBKR_LAST_RUN, sentinel_last_run, "start 실패 시 LAST_RUN 도 롤백돼야 한다(13R MAJOR)")

    def test_missing_script_resets_inflight(self):
        """monitor script 누락 시에도 in-flight 플래그가 영구 고착되지 않는다(Codex 10R MAJOR)."""
        mod = self.mod
        mod._IBKR_RUN_IN_PROGRESS = True  # GET 이 켠 상태를 모사
        with tempfile.TemporaryDirectory() as d:
            errlog = Path(d) / "e.log"
            with mock.patch.object(mod, "PROJECT_ROOT", Path(d)), \
                 mock.patch.object(mod, "_IBKR_ERROR_LOG_PATH", errlog):
                mod._run_ibkr_monitor_background()  # script 없음 → 예외 → finally 가 복구
        self.assertFalse(mod._IBKR_RUN_IN_PROGRESS)


class IbkrConfiguredModeTests(unittest.TestCase):
    """offline fallback 의 mode/포트 선택 근거(_ibkr_configured_mode), Codex 9R/11R."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def test_env_mode_resolution(self):
        """monitor 와 동일 규칙: 정확히 'paper' 만 paper, 그 외(live/garbage/empty)는 live(포트 4001)."""
        import os
        mod = self.mod
        cases = {"paper": "paper", "live": "live", "LIVE": "live", " paper ": "paper",
                 "": "live", "garbage": "live"}
        for env_val, expected in cases.items():
            with mock.patch.dict(os.environ, {"IBKR_TRADING_MODE": env_val}):
                self.assertEqual(mod._ibkr_configured_mode(), expected, env_val)

    def test_unset_env_resolves_paper(self):
        """env 미설정 시 monitor 기본(paper, 포트 4002)과 동일하게 paper."""
        import os
        mod = self.mod
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(mod._ibkr_configured_mode(), "paper")


class IbkrErrorLogTests(unittest.TestCase):
    """_ibkr_log_error 의 롤오버(무한 성장 방지, Codex 6R MINOR)."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def test_rolls_over_when_over_cap(self):
        mod = self.mod
        with tempfile.TemporaryDirectory() as d:
            errlog = Path(d) / "e.log"
            errlog.write_text("x" * (mod._IBKR_ERROR_LOG_MAX_BYTES + 10), encoding="utf-8")
            with mock.patch.object(mod, "_IBKR_ERROR_LOG_PATH", errlog):
                mod._ibkr_log_error("새 항목")
            # 새 로그는 작은 크기로 시작하고, 이전 큰 로그는 .1 로 보존
            self.assertTrue(errlog.exists() and errlog.stat().st_size < 10_000)
            self.assertTrue((Path(d) / "e.log.1").exists())
            self.assertIn("새 항목", errlog.read_text())


if __name__ == "__main__":
    unittest.main()
