import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.summarize_openclaw_route_audit import build_summary, main, _build_slack_summary


class OpenClawRouteAuditSummaryTests(unittest.TestCase):
    def test_build_summary_includes_failure_memory_candidate_threshold(self):
        records = [
            {
                "ts": "2026-05-30T10:00:00",
                "route": "contextual_risk_block",
                "risk_level": "high",
                "blocked": True,
                "message": "그거 보내줘",
                "reason": "민감한 대상",
                "flags": ["contextual_high_risk_reference"],
                "context_sensitive_terms": ["초안"],
            },
            {
                "ts": "2026-05-31T10:00:00",
                "route": "contextual_risk_block",
                "risk_level": "high",
                "blocked": True,
                "message": "그거 올려줘",
                "reason": "민감한 대상",
                "flags": ["contextual_high_risk_reference"],
                "context_sensitive_terms": ["뉴스레터"],
            },
        ]

        summary = build_summary(records, generated_for="2026-05-18", label="daily", change_date="2026-05-31")

        self.assertIn("records_reviewed: 2", summary)
        self.assertIn("OpenClaw Route Audit Summary (daily)", summary)
        self.assertIn("Candidate: contextual_risk_block", summary)
        self.assertIn("Do not automatically append", summary)

    def test_build_summary_includes_target_query_routing(self):
        records = [
            {
                "ts": "2026-05-30T09:00:00",
                "kind": "route",
                "route": "economy_chat",
                "risk_level": "low",
                "blocked": False,
                "message": "이번 주 top risk 5개와 즉시 조치안을 요약해줘",
                "flags": [],
                "model": "claude-haiku-4-5",
            },
            {
                "ts": "2026-05-31T09:00:00",
                "kind": "route",
                "route": "deterministic_status_brief",
                "risk_level": "low",
                "blocked": False,
                "message": "이번 주 top risk 5개와 즉시 조치안을 요약해줘",
                "flags": [],
                "model": None,
            },
            {
                "ts": "2026-05-31T09:10:00",
                "kind": "route",
                "route": "deterministic_gmail_summary",
                "risk_level": "low",
                "blocked": False,
                "message": "오늘 온 메일 보여줘",
                "flags": [],
                "model": None,
            },
            {
                "ts": "2026-05-31T09:10:01",
                "kind": "response_metric",
                "route": "deterministic_gmail_summary",
                "message": "오늘 온 메일 보여줘",
                "response_chars": 88,
            },
            {
                "ts": "2026-05-31T09:00:01",
                "kind": "response_metric",
                "route": "deterministic_status_brief",
                "message": "이번 주 top risk 5개와 즉시 조치안을 요약해줘",
                "response_chars": 132,
            },
        ]

        summary = build_summary(records, generated_for="2026-05-31", label="daily", change_date="2026-05-31")

        self.assertIn("## Target Query Routing", summary)
        self.assertIn("### top risk / risk", summary)
        self.assertIn("before_2026-05-31: total=1, premium=0", summary)
        self.assertIn("on_after_2026-05-31: total=1, premium=0", summary)
        self.assertIn("### mail / gmail", summary)
        self.assertIn("route::deterministic_gmail_summary = 1", summary)
        self.assertIn("## Response Length", summary)
        self.assertIn("overall_avg_response_chars: 110.0", summary)

    def test_build_slack_summary_includes_route_mix_and_change_metrics(self):
        records = [
            {
                "ts": "2026-05-24T09:00:00",
                "kind": "route",
                "route": "economy_chat",
                "message": "이번 주 top risk 5개와 즉시 조치안을 요약해줘",
            },
            {
                "ts": "2026-05-31T09:00:00",
                "kind": "route",
                "route": "deterministic_status_brief",
                "message": "이번 주 top risk 5개와 즉시 조치안을 요약해줘",
            },
            {
                "ts": "2026-05-31T09:10:00",
                "kind": "route",
                "route": "deterministic_gmail_summary",
                "message": "오늘 온 메일 보여줘",
            },
            {
                "ts": "2026-05-31T09:20:00",
                "kind": "route",
                "route": "premium_chat",
                "message": "가격 바꿀까?",
            },
            {
                "ts": "2026-05-24T09:20:01",
                "kind": "response_metric",
                "route": "premium_chat",
                "message": "가격 바꿀까?",
                "response_chars": 300,
            },
            {
                "ts": "2026-05-31T09:20:01",
                "kind": "response_metric",
                "route": "premium_chat",
                "message": "가격 바꿀까?",
                "response_chars": 180,
            },
        ]

        text = _build_slack_summary(records, change_date="2026-05-31")

        self.assertIn("route mix: deterministic 2 / local 0 / economy 1 / premium 1", text)
        self.assertIn("avg response chars: 240.0", text)
        self.assertIn("avg response chars WoW: 180.0 (-120.0 vs prev 300.0)", text)
        self.assertIn("top risk after 2026-05-31: premium 0/1", text)
        self.assertIn("mail after 2026-05-31: premium 0/1", text)

    def test_build_summary_includes_weekly_response_delta(self):
        records = [
            {
                "ts": "2026-05-24T09:00:01",
                "kind": "response_metric",
                "route": "premium_chat",
                "message": "prev week",
                "response_chars": 300,
            },
            {
                "ts": "2026-05-31T09:00:01",
                "kind": "response_metric",
                "route": "deterministic_status_brief",
                "message": "current week",
                "response_chars": 180,
            },
        ]

        summary = build_summary(records, generated_for="2026-05-31", label="daily", change_date="2026-05-31")

        self.assertIn("trailing_7d_avg_chars: 180.0", summary)
        self.assertIn("previous_7d_avg_chars: 300.0", summary)
        self.assertIn("trailing_7d_delta_chars: -120.0", summary)

    def test_main_writes_summary_file(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit_path = root / "audit.jsonl"
            output_dir = root / "out"
            audit_path.write_text(
                json.dumps(
                    {
                        "route": "local_chat",
                        "risk_level": "low",
                        "blocked": False,
                        "message": "안녕",
                        "flags": [],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            import sys

            old_argv = sys.argv
            try:
                sys.argv = [
                    "summarize_openclaw_route_audit.py",
                    "--audit-path",
                    str(audit_path),
                    "--output-dir",
                    str(output_dir),
                    "--date",
                    "2026-05-18",
                    "--output-name",
                    "custom_audit.md",
                ]
                rc = main()
            finally:
                sys.argv = old_argv

            self.assertEqual(rc, 0)
            output_path = output_dir / "custom_audit.md"
            self.assertTrue(output_path.exists())
            self.assertIn("records_reviewed: 1", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
