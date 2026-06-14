import json
import tempfile
import unittest
from pathlib import Path

from scripts import edu_data_analysis_agent as mod


class EduDataAnalysisAgentTests(unittest.TestCase):
    def setUp(self):
        self.signature = mod.get_embedding_signature()

    def _write_json(self, path: Path, payload) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_build_dataframe_dedupes_duplicate_rss_while_preserving_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research_dir = root / "research"
            transcripts_dir = root / "transcripts"
            research_dir.mkdir()
            transcripts_dir.mkdir()

            self._write_json(
                research_dir / "rss_collected.json",
                [
                    {
                        "source": "EdSurge",
                        "title": "AI homework pressure",
                        "link": "https://example.com/1",
                        "published": "Thu, 21 May 2026 13:34:04 -0700",
                        "summary": "Parents say AI homework shortcuts are making after-school routines harder.",
                        "tags": ["EdTech"],
                    },
                    {
                        "source": "EdSurge",
                        "title": "AI homework pressure",
                        "link": "https://example.com/1",
                        "published": "Thu, 21 May 2026 13:34:04 -0700",
                        "summary": "Parents say AI homework shortcuts are making after-school routines harder.",
                        "tags": ["EdTech"],
                    },
                ],
            )
            self._write_json(
                root / "anchors.json",
                {"items": [{"id": "anchor-1", "type": "전문가 발언", "segment": "parent", "cite": "AI를 바로 답으로 쓰게 두면 질문 근육이 약해집니다.", "source": "Example Expert"}]},
            )

            frame, dlq, run = mod.build_knowledge_dataframe(
                research_dirs=[research_dir],
                transcripts_dir=transcripts_dir,
                anchors_path=root / "anchors.json",
                correlation_id="dedupe-test",
            )

            self.assertEqual(run.skipped_count, 1)
            self.assertEqual(len(frame), 2)
            self.assertEqual(len(dlq), 0)
            self.assertEqual(frame["natural_key"].nunique(), 2)
            self.assertEqual((frame["source"] == "EdSurge").sum(), 1)
            self.assertEqual((frame["source"] == "EvidenceAnchor").sum(), 1)

    def test_schema_tolerance_isolates_bad_source_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research_dir = root / "research"
            transcripts_dir = root / "transcripts"
            research_dir.mkdir()
            transcripts_dir.mkdir()

            self._write_json(
                research_dir / "rss_collected.json",
                [
                    {
                        "source": "EdSurge",
                        "title": "Useful signal",
                        "link": "https://example.com/good",
                        "published": "2026-06-01T00:00:00Z",
                        "summary": "A well-formed article summary about family AI rules.",
                        "tags": ["family"],
                    }
                ],
            )
            (research_dir / "reddit_collected.json").write_text("{not-json", encoding="utf-8")
            self._write_json(root / "anchors.json", {"items": []})

            frame, dlq, run = mod.build_knowledge_dataframe(
                research_dirs=[research_dir],
                transcripts_dir=transcripts_dir,
                anchors_path=root / "anchors.json",
                correlation_id="tolerance-test",
            )

            self.assertEqual(len(frame), 1)
            self.assertEqual(run.adapter_failures, 1)
            self.assertTrue(any(entry.reason_code == "parse_error" for entry in dlq))
            self.assertGreaterEqual(run.input_count, len(dlq))

    def test_validation_routes_missing_source_url_to_dlq(self):
        row = {
            "source_ref": None,
            "natural_key": "nk",
            "source": "Example",
            "source_id": "1",
            "source_url": "",
            "source_kind": "general_reference",
            "provenance": "collected",
            "rights_class": "fair_excerpt",
            "reuse_scope": "customer_facing",
            "excerpt_max_chars": 120,
            "verbatim_allowed": False,
            "segment": "parent",
            "item_type": "rss_article",
            "title": "Title",
            "body": "This body is long enough to be considered valid text for the validator.",
            "cite": "This body is long enough.",
            "lang": "en",
            "quality_score": 70.0,
            "keywords": ["body"],
            "emb_model": self.signature["model"],
            "emb_dim": self.signature["dim"],
            "collected_at": "2026-06-14T00:00:00+00:00",
        }
        frame, dlq = mod.validate_knowledge_dataframe(
            mod.pd.DataFrame([row]),
            self.signature,
            "validate-test",
        )

        self.assertTrue(frame.empty)
        self.assertEqual(len(dlq), 1)
        self.assertEqual(dlq[0].reason_code, "missing_source_url")

    def test_validation_rejects_embedding_signature_mismatch(self):
        row = {
            "source_ref": None,
            "natural_key": "nk2",
            "source": "Example",
            "source_id": "2",
            "source_url": "https://example.com/2",
            "source_kind": "general_reference",
            "provenance": "collected",
            "rights_class": "fair_excerpt",
            "reuse_scope": "customer_facing",
            "excerpt_max_chars": 120,
            "verbatim_allowed": False,
            "segment": "parent",
            "item_type": "rss_article",
            "title": "Title",
            "body": "This body is long enough to be considered valid text for the validator.",
            "cite": "This body is long enough.",
            "lang": "en",
            "quality_score": 70.0,
            "keywords": ["body"],
            "emb_model": self.signature["model"],
            "emb_dim": self.signature["dim"] + 1,
            "collected_at": "2026-06-14T00:00:00+00:00",
        }
        frame, dlq = mod.validate_knowledge_dataframe(
            mod.pd.DataFrame([row]),
            self.signature,
            "embed-test",
        )

        self.assertTrue(frame.empty)
        self.assertEqual(dlq[0].reason_code, "embedding_signature_mismatch")

    def test_anchor_items_default_to_fair_excerpt_not_public_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchor_path = root / "anchors.json"
            self._write_json(
                anchor_path,
                {
                    "items": [
                        {
                            "id": "anchor-1",
                            "type": "전문가 발언",
                            "segment": "parent",
                            "cite": "질문 없이 바로 답을 얻는 습관은 학습 근육을 약하게 만들 수 있습니다.",
                            "source": "Example Expert",
                        }
                    ]
                },
            )
            items, dlq = mod._build_anchor_items(anchor_path, self.signature, "anchor-test")

            self.assertEqual(len(dlq), 0)
            self.assertEqual(items[0].rights_class, "fair_excerpt")
            self.assertFalse(items[0].verbatim_allowed)
            self.assertEqual(items[0].reuse_scope, "customer_facing")

    def test_anchor_dlq_uses_run_correlation_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_anchor_path = root / "anchors.json"
            bad_anchor_path.write_text("{bad-json", encoding="utf-8")

            items, dlq = mod._build_anchor_items(bad_anchor_path, self.signature, "corr-123")

            self.assertEqual(items, [])
            self.assertEqual(len(dlq), 1)
            self.assertEqual(dlq[0].correlation_id, "corr-123")

    def test_customer_facing_body_is_clipped_to_excerpt_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "eric_collected.json"
            path.write_text("[]", encoding="utf-8")
            row = {
                "source": "ERIC",
                "title": "Title",
                "description": "x" * 400,
                "author": "Author",
                "query": "Query",
                "url": "https://example.com/doc",
                "year": 2026,
            }
            item = mod._normalize_row("eric", row, path, self.signature)

            self.assertEqual(item.reuse_scope, "customer_facing")
            self.assertLessEqual(len(item.body), item.excerpt_max_chars)

    def test_dlq_indexdef_validation_matches_expected_contract(self):
        indexdef = (
            "CREATE UNIQUE INDEX idx_dlq_unresolved_reuse ON public.dead_letter_queue "
            "USING btree (pipeline_name, tier, external_key, reason_code, item_type) "
            "WHERE (resolved = false)"
        )
        self.assertTrue(mod._dlq_index_contract_ok(indexdef))

    def test_customer_facing_view_contract_matches_expected_predicate(self):
        viewdef = (
            " SELECT edu_knowledge_items.id, edu_knowledge_items.source "
            "FROM public.edu_knowledge_items "
            "WHERE ((reuse_scope = 'customer_facing'::text) "
            "AND (provenance = ANY (ARRAY['collected'::text, 'curated'::text])) "
            "AND (rights_class = ANY (ARRAY['public'::text, 'fair_excerpt'::text])) "
            "AND (excerpt_max_chars > 0));"
        )
        self.assertTrue(mod._customer_facing_view_contract_ok(viewdef))

    def test_preflight_bootstrap_requires_text_compatible_correlation_id(self):
        class FakeCursor:
            def execute(self, _query):
                return None

            def fetchall(self):
                return [
                    ("pipeline_runs", "id", "bigint"),
                    ("pipeline_runs", "correlation_id", "uuid"),
                    ("pipeline_runs", "pipeline_name", "text"),
                    ("pipeline_runs", "status", "text"),
                    ("pipeline_runs", "error", "text"),
                    ("pipeline_runs", "started_at", "timestamp without time zone"),
                    ("pipeline_runs", "finished_at", "timestamp without time zone"),
                    ("pipeline_runs", "input_count", "integer"),
                    ("pipeline_runs", "success_count", "integer"),
                    ("pipeline_runs", "skipped_count", "integer"),
                    ("pipeline_runs", "dlq_count", "integer"),
                    ("pipeline_runs", "adapter_failures", "integer"),
                ]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeConn:
            def cursor(self):
                return FakeCursor()

        with self.assertRaisesRegex(RuntimeError, "schema_preflight_invalid_column_type:pipeline_runs.correlation_id:uuid"):
            mod._preflight_bootstrap(FakeConn())

    def test_write_dlq_updates_canonical_correlation_id_on_reuse(self):
        executed: list[tuple[str, tuple]] = []

        class FakeCursor:
            def execute(self, query, params):
                executed.append((query, params))

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        class FakeConn:
            def cursor(self):
                return FakeCursor()

        mod._write_dlq(
            FakeConn(),
            [
                mod.DlqRecord(
                    tier=1,
                    item_type="rss_article",
                    error_message="body_too_short",
                    raw_data={"natural_key": "nk-1"},
                    reason_code="body_too_short",
                    source_name="EdSurge",
                    correlation_id="corr-new",
                )
            ],
        )

        self.assertEqual(len(executed), 1)
        self.assertIn("correlation_id = EXCLUDED.correlation_id", executed[0][0])
        self.assertEqual(executed[0][1][7], "corr-new")


if __name__ == "__main__":
    unittest.main()
