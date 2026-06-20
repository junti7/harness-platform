import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


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


class EduCustomerFacingRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_backend_main()

    def test_db_bundle_reads_customer_facing_view_only(self):
        captured = {}

        def fake_execute_query(query, params=None, fetch=False):
            captured["query"] = query
            captured["params"] = params
            captured["fetch"] = fetch
            return [
                {
                    "id": 101,
                    "source": "OECD Education Report",
                    "source_kind": "research_policy",
                    "segment": "parent",
                    "type": "report",
                    "title": "Parent AI use",
                    "body": "중학생 숙제에서 AI를 답안기로만 쓰지 않도록 질문 설계를 같이 보라는 내용입니다.",
                    "cite": "중학생 숙제에서 AI를 답안기로만 쓰지 않도록 질문 설계를 같이 보라는 내용입니다.",
                    "quality_score": 9.2,
                    "rights_class": "fair_excerpt",
                    "excerpt_max_chars": 220,
                    "verbatim_allowed": False,
                    "keywords": ["중학생", "숙제", "AI"],
                }
            ]

        with patch.object(self.mod, "execute_query", side_effect=fake_execute_query):
            bundle = self.mod._edu_db_customer_facing_bundle("중학생 숙제 AI", segment="parent", k=3)

        self.assertIsNotNone(bundle)
        self.assertIn("FROM edu_knowledge_items_customer_facing", captured["query"])
        self.assertNotIn("FROM edu_knowledge_items ", captured["query"])
        self.assertTrue(captured["fetch"])
        self.assertEqual(bundle["source_kinds"], ["research_policy"])

    def test_retrieve_evidence_prefers_db_customer_facing_mode(self):
        db_bundle = {
            "items": [],
            "lines": ["- (report) grounded cite\n  └ 출처: grounded src"],
            "source_kinds": ["research_policy"],
            "mode": "db_customer_facing",
        }
        with patch.object(self.mod, "_edu_db_customer_facing_bundle", return_value=db_bundle):
            with patch.object(self.mod, "_edu_ranked_matches", side_effect=AssertionError("index path should not run")):
                text, meta = self.mod._retrieve_evidence("중학생 숙제 AI", segment="parent", k=3)

        self.assertIn("grounded cite", text)
        self.assertEqual(meta["mode"], "db_customer_facing")
        self.assertEqual(meta["source_kinds"], ["research_policy"])

    def test_retrieve_evidence_falls_back_to_index_when_db_unavailable(self):
        ranked = [
            (
                {
                    "id": "legacy-1",
                    "type": "report",
                    "cite": "기존 인덱스에서도 근거를 회수합니다.",
                    "source": "legacy source",
                    "source_kind": "research_policy",
                },
                0.91,
            )
        ]
        with patch.object(self.mod, "_edu_db_customer_facing_bundle", return_value=None):
            with patch.object(self.mod, "_edu_ranked_matches", return_value=ranked):
                text, meta = self.mod._retrieve_evidence("직장인 AI 불안", segment="worker", k=2)

        self.assertIn("기존 인덱스에서도 근거를 회수합니다.", text)
        self.assertEqual(meta["mode"], "indexed")
        self.assertEqual(meta["source_kinds"], ["research_policy"])


if __name__ == "__main__":
    unittest.main()
