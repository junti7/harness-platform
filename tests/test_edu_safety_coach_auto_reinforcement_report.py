import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


def _load_script():
    module_name = "edu_safety_coach_auto_reinforcement_report_for_tests"
    if module_name in sys.modules:
        return sys.modules[module_name]
    path = Path(__file__).resolve().parents[1] / "scripts" / "report_edu_safety_coach_auto_reinforcement.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeBackend:
    def __init__(self, *, summary, pending=None):
        self.schema_ensured = False
        self.summary = summary
        self.pending = pending or []
        self.queries = []

    def _ensure_edu_case_schema(self):
        self.schema_ensured = True

    def _edu_execute(self, query, params=None, *, fetch=False):
        self.queries.append((query, params, fetch))
        if "WITH downvotes" in query:
            return [self.summary]
        return self.pending


class EduSafetyCoachAutoReinforcementReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = _load_script()

    def test_report_ok_when_all_downvotes_reviewed_within_sla(self):
        fake = FakeBackend(
            summary={
                "downvote_count": 2,
                "reviewed_count": 2,
                "pending_count": 0,
                "reviewed_within_sla_count": 2,
                "stale_pending_count": 0,
                "last_downvote_at": datetime(2026, 6, 27, tzinfo=timezone.utc),
                "last_review_at": datetime(2026, 6, 27, tzinfo=timezone.utc),
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy_candidates.jsonl"
            path.write_text(json.dumps({"candidate_id": "c1", "issues": ["x"], "highest_severity": "major"}) + "\n", encoding="utf-8")
            with patch.object(self.script, "_load_backend", return_value=fake), patch.object(self.script, "POLICY_CANDIDATE_PATH", path):
                report = self.script.run_report(lookback_days=7, sla_minutes=5)

        self.assertTrue(report["ok"])
        self.assertTrue(fake.schema_ensured)
        self.assertEqual(report["review_completion_rate"], 1.0)
        self.assertEqual(report["review_sla_rate"], 1.0)
        self.assertEqual(report["policy_candidates"]["count"], 1)

    def test_report_fails_when_stale_pending_exists(self):
        fake = FakeBackend(
            summary={
                "downvote_count": 3,
                "reviewed_count": 2,
                "pending_count": 1,
                "reviewed_within_sla_count": 2,
                "stale_pending_count": 1,
                "last_downvote_at": None,
                "last_review_at": None,
            },
            pending=[
                {
                    "case_id": 123,
                    "email": "x@example.com",
                    "created_at": datetime(2026, 6, 27, tzinfo=timezone.utc),
                    "event_payload": {"question": "왜 이렇게 답해?", "answer_version": "v1"},
                }
            ],
        )
        with patch.object(self.script, "_load_backend", return_value=fake):
            report = self.script.run_report(lookback_days=7, sla_minutes=5)

        self.assertFalse(report["ok"])
        self.assertEqual(report["stale_pending_count"], 1)
        self.assertEqual(report["pending_samples"][0]["question"], "왜 이렇게 답해?")


if __name__ == "__main__":
    unittest.main()
