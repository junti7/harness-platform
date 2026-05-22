import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.summarize_openclaw_route_audit import build_summary, main


class OpenClawRouteAuditSummaryTests(unittest.TestCase):
    def test_build_summary_includes_failure_memory_candidate_threshold(self):
        records = [
            {
                "route": "contextual_risk_block",
                "risk_level": "high",
                "blocked": True,
                "message": "그거 보내줘",
                "reason": "민감한 대상",
                "flags": ["contextual_high_risk_reference"],
                "context_sensitive_terms": ["초안"],
            },
            {
                "route": "contextual_risk_block",
                "risk_level": "high",
                "blocked": True,
                "message": "그거 올려줘",
                "reason": "민감한 대상",
                "flags": ["contextual_high_risk_reference"],
                "context_sensitive_terms": ["뉴스레터"],
            },
        ]

        summary = build_summary(records, generated_for="2026-05-18", label="daily")

        self.assertIn("records_reviewed: 2", summary)
        self.assertIn("OpenClaw Route Audit Summary (daily)", summary)
        self.assertIn("Candidate: contextual_risk_block", summary)
        self.assertIn("Do not automatically append", summary)

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
