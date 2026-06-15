"""pipeline_backlog 엔드포인트 회귀 가드.

검증 포인트(Red Team Codex v3 MAJOR 반영):
  1. 정제 깔때기(filtered/refined/backlog)는 *단일 쿼리·단일 스냅샷*으로 읽어야 한다
     (4개 순차 쿼리 시 동시 쓰기 중 refined+backlog==filtered 불변식이 깨짐).
  2. 단위 정합: refined_total + refine_backlog == filtered_total.
  3. ETA = backlog / per_hour, 처리율 0이면 None(div-by-zero 방지).
  4. domain 파라미터가 SQL 바인딩과 응답에 그대로 반영된다.
"""

import importlib.util
import sys
import unittest
from pathlib import Path


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


class PipelineBacklogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def _run(self, funnel_row, raw_pending=0, domain="edu_consulting"):
        """_execute_query 를 가로채 쿼리별 canned row 를 돌려준다. 실행된 쿼리도 기록."""
        self.mod._BACKLOG_CACHE.clear()  # TTL 캐시가 테스트 간 결과를 오염시키지 않도록 초기화
        executed = []

        def fake_execute_query(query, params=None, fetch=False):
            executed.append((query, params))
            if "raw_signals" in query:
                return [{"raw_pending": raw_pending}]
            return [funnel_row]

        orig = self.mod._execute_query
        self.mod._execute_query = fake_execute_query
        try:
            result = self.mod.pipeline_backlog(domain=domain, _=None)
        finally:
            self.mod._execute_query = orig
        return result, executed

    def test_single_snapshot_query_for_funnel(self):
        """정제 깔때기 4개 지표는 1개 쿼리(단일 스냅샷)에서 나와야 한다."""
        funnel = {"filtered_total": 100, "refine_backlog": 40, "refined_total": 60, "refined_per_hour": 5}
        _, executed = self._run(funnel)
        funnel_queries = [q for q, _ in executed if "filtered_signals" in q]
        self.assertEqual(len(funnel_queries), 1, "정제 깔때기는 단일 쿼리여야 한다")
        q = funnel_queries[0]
        # 단일 스냅샷 + 중복 방지의 핵심 구문이 유지되는지 가드
        self.assertIn("LEFT JOIN refined_outputs", q)
        self.assertIn("FILTER", q)
        self.assertIn("DISTINCT", q)

    def test_unit_reconciliation(self):
        """refined_total + refine_backlog == filtered_total (단위 정합)."""
        funnel = {"filtered_total": 100, "refine_backlog": 40, "refined_total": 60, "refined_per_hour": 5}
        result, _ = self._run(funnel)
        self.assertEqual(result["refined_total"] + result["refine_backlog"], result["filtered_total"])

    def test_eta_computation(self):
        funnel = {"filtered_total": 100, "refine_backlog": 40, "refined_total": 60, "refined_per_hour": 8}
        result, _ = self._run(funnel)
        self.assertEqual(result["eta_hours"], 5.0)  # 40 / 8

    def test_eta_none_when_no_throughput(self):
        funnel = {"filtered_total": 100, "refine_backlog": 40, "refined_total": 60, "refined_per_hour": 0}
        result, _ = self._run(funnel)
        self.assertIsNone(result["eta_hours"])

    def test_raw_pending_uses_domain_coalesce(self):
        """raw_signals 는 collector 가 domain 컬럼을 비워 넣는 전이 row 가 있으므로

        get_pipeline_signals 와 동일하게 coalesce(domain, raw_data->>'domain', '') 로 해석해야
        '수집 직후~태깅 전 pending' 을 누락하지 않는다.
        """
        funnel = {"filtered_total": 1, "refine_backlog": 1, "refined_total": 0, "refined_per_hour": 0}
        _, executed = self._run(funnel)
        raw_queries = [q for q, _ in executed if "raw_signals" in q]
        self.assertEqual(len(raw_queries), 1)
        self.assertIn("coalesce(domain, raw_data->>'domain', '')", raw_queries[0])

    def test_filtered_uses_plain_domain(self):
        """filtered_signals 는 필터가 domain 을 항상 채우므로 plain f.domain = %s 로 집계한다."""
        funnel = {"filtered_total": 1, "refine_backlog": 1, "refined_total": 0, "refined_per_hour": 0}
        _, executed = self._run(funnel)
        funnel_queries = [q for q, _ in executed if "filtered_signals" in q and "raw_signals" not in q]
        self.assertEqual(len(funnel_queries), 1)
        self.assertIn("f.domain = %s", funnel_queries[0])

    def test_disallowed_domain_rejected(self):
        """allowlist 밖 도메인은 400 으로 거부(고비용 쿼리 남용·캐시 키 증식 방지)."""
        self.mod._BACKLOG_CACHE.clear()
        with self.assertRaises(self.mod.HTTPException) as ctx:
            self.mod.pipeline_backlog(domain="'; DROP TABLE x; --", _=None)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_ttl_cache_avoids_second_db_hit(self):
        """TTL 윈도 내 재호출은 DB 를 다시 치지 않는다(폴링 부하 방지)."""
        self.mod._BACKLOG_CACHE.clear()
        calls = {"n": 0}

        def fake_execute_query(query, params=None, fetch=False):
            calls["n"] += 1
            if "raw_signals" in query:
                return [{"raw_pending": 0}]
            return [{"filtered_total": 10, "refine_backlog": 4, "refined_total": 6, "refined_per_hour": 2}]

        orig = self.mod._execute_query
        self.mod._execute_query = fake_execute_query
        try:
            self.mod.pipeline_backlog(domain="edu_consulting", _=None)
            first = calls["n"]
            self.mod.pipeline_backlog(domain="edu_consulting", _=None)
            self.assertEqual(calls["n"], first, "TTL 내 두 번째 호출은 캐시여야 한다")
        finally:
            self.mod._execute_query = orig
            self.mod._BACKLOG_CACHE.clear()

    def test_domain_is_bound_and_echoed(self):
        funnel = {"filtered_total": 1, "refine_backlog": 1, "refined_total": 0, "refined_per_hour": 0}
        result, executed = self._run(funnel, domain="physical_ai")
        self.assertEqual(result["domain"], "physical_ai")
        for _q, params in executed:
            self.assertEqual(params, ("physical_ai",))

    def test_empty_rows_safe(self):
        """빈 결과(테이블 비었거나 도메인 미존재)에서도 0/None 으로 안전 반환."""
        self.mod._BACKLOG_CACHE.clear()
        executed = []

        def fake_execute_query(query, params=None, fetch=False):
            executed.append(query)
            return []

        orig = self.mod._execute_query
        self.mod._execute_query = fake_execute_query
        try:
            result = self.mod.pipeline_backlog(domain="edu_consulting", _=None)
        finally:
            self.mod._execute_query = orig
        self.assertEqual(result["refine_backlog"], 0)
        self.assertEqual(result["filtered_total"], 0)
        self.assertIsNone(result["eta_hours"])


if __name__ == "__main__":
    unittest.main()
