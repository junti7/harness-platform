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
        self.mod._EDU_CF_TABLE_READY = None

        def fake_execute_query(query, params=None, fetch=False):
            captured["query"] = query
            captured["params"] = params
            captured["fetch"] = fetch
            return [
                {
                    "id": 101,
                    "source": "OECD Education Report",
                    "source_ref": "https://example.org/oecd-parent-ai",
                    "source_url": "https://example.org/oecd-parent-ai",
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
                    "source_url": "https://example.org/legacy-source",
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

    def test_db_bundle_caches_missing_customer_facing_table(self):
        self.mod._EDU_CF_TABLE_READY = None

        class UndefinedTable(Exception):
            pass

        with (
            patch.object(self.mod, "execute_query", side_effect=UndefinedTable("relation does not exist")) as mocked_query,
            patch.object(self.mod, "_edu_runtime_event"),
        ):
            first = self.mod._edu_db_customer_facing_bundle("중학생 숙제 AI", segment="parent", k=3)
            second = self.mod._edu_db_customer_facing_bundle("중학생 숙제 AI", segment="parent", k=3)

        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(mocked_query.call_count, 1)
        self.assertFalse(self.mod._EDU_CF_TABLE_READY)
        self.mod._EDU_CF_TABLE_READY = None

    def test_ranked_matches_blocks_legacy_index_model_mismatch(self):
        index = {
            "provider": None,
            "model": "gemini-embedding-001",
            "dim": 768,
            "items": [
                {
                    "id": "legacy-1",
                    "emb": [1.0, 0.0],
                    "cite": "중학생 숙제에서 AI 사용을 지도하는 근거입니다.",
                    "source": "legacy source",
                }
            ],
        }
        with (
            patch.object(self.mod, "_load_rag_index", return_value=index),
            patch("core.embeddings.embedding_backend_signature", return_value={"provider": "ollama", "model": "nomic-embed-text", "dim": 768}),
            patch("core.embeddings.embed_query", side_effect=AssertionError("mismatched index should not embed")),
            patch.object(self.mod, "_edu_runtime_event") as mocked_event,
        ):
            ranked = self.mod._edu_ranked_matches("중학생 숙제 AI", limit=3)

        self.assertIsNone(ranked)
        mocked_event.assert_called_once()
        self.assertEqual(mocked_event.call_args.args[0], "edu_rag_signature_mismatch")

    def test_ranked_matches_falls_back_to_lexical_when_embedding_fails(self):
        index = {
            "provider": None,
            "model": "gemini-embedding-001",
            "dim": 768,
            "items": [
                {
                    "id": "legacy-1",
                    "segment": "parent",
                    "emb": [1.0, 0.0],
                    "cite": "중학생 숙제에서 AI를 답안기로만 쓰지 않도록 부모가 풀이 과정을 같이 점검합니다.",
                    "source": "OECD Education Report",
                    "source_kind": "research_policy",
                    "keywords": ["중학생", "숙제", "AI"],
                    "quality_score": 9.0,
                },
                {
                    "id": "legacy-2",
                    "segment": "worker",
                    "emb": [0.0, 1.0],
                    "cite": "직장인의 반복 업무 자동화에 관한 근거입니다.",
                    "source": "Worker Report",
                    "source_kind": "research_policy",
                    "keywords": ["직장인"],
                    "quality_score": 7.0,
                },
            ],
        }
        with (
            patch.object(self.mod, "_load_rag_index", return_value=index),
            patch("core.embeddings.embedding_backend_signature", return_value={"provider": "google", "model": "gemini-embedding-001", "dim": 768}),
            patch("core.embeddings.embed_query", side_effect=RuntimeError("429 RESOURCE_EXHAUSTED")),
            patch.object(self.mod, "_edu_runtime_event") as mocked_event,
        ):
            ranked = self.mod._edu_ranked_matches("중학생 숙제 AI", limit=3, segment="parent")

        self.assertIsNotNone(ranked)
        self.assertEqual(ranked[0][0]["id"], "legacy-1")
        mocked_event.assert_called_once()
        self.assertEqual(mocked_event.call_args.args[0], "edu_rag_embedding_retrieval_failed")


if __name__ == "__main__":
    unittest.main()
