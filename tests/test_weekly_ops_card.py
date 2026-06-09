import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts.summarize_weekly_ops_card import build_summary, _build_slack_summary, main


class WeeklyOpsCardTests(unittest.TestCase):
    def test_build_summary_includes_combined_sections(self):
        route_records = [
            {"ts": "2026-06-01T10:00:00", "kind": "route", "route": "deterministic_status_brief", "message": "status"},
            {"ts": "2026-06-01T10:00:01", "kind": "response_metric", "route": "deterministic_status_brief", "response_chars": 120},
        ]
        conference_records = [
            {"posted_at": "2026-06-01T10:00:00", "text_markdown": "*Vision(상품기획팀)*:\n짧게 답합니다."},
            {"posted_at": "2026-06-01T10:01:00", "text_markdown": "*TARS(엔지니어링팀)*:\nupdate_topic(foo)\n노이즈"},
        ]

        with patch(
            "scripts.summarize_weekly_ops_card.load_recent_fallback_events",
            return_value=[
                {
                    "event_type": "fallback_activated",
                    "persona_display": "Friday(사업운영팀)",
                    "primary_provider": "claude",
                    "active_provider": "gemini",
                    "reason": "usage_limit_exceeded",
                }
            ],
        ), patch(
            "scripts.summarize_weekly_ops_card._latest_goal_forecast",
            return_value={
                "title": "Free subscriber growth",
                "probability_to_hit": 0.55,
                "health_status": "yellow",
                "recommended_mode": "local_revision",
                "actual_value": 0,
                "expected_value": 12,
            },
        ), patch(
            "scripts.summarize_weekly_ops_card._ops_finance_snapshot",
            return_value={
                "total_spent_usd": 100.0,
                "remaining_budget_usd": 6900.0,
                "avg_daily_burn_usd": 3.0,
                "runway_days": 2300.0,
            },
        ):
            summary = build_summary(route_records, conference_records, generated_for="2026-06-01")

        self.assertIn("CEO Weekly Ops Card - 2026-06-01", summary)
        self.assertIn("## Control Plane", summary)
        self.assertIn("## Conference Room", summary)
        self.assertIn("## Provider Incidents", summary)
        self.assertIn("fallback_activated: 1", summary)
        self.assertIn("## Goal Forecast", summary)
        self.assertIn("## Finance", summary)

    def test_build_slack_summary_includes_combined_metrics(self):
        route_records = [
            {"ts": "2026-06-01T10:00:00", "kind": "route", "route": "premium_chat", "message": "가격"},
            {"ts": "2026-06-01T10:00:01", "kind": "response_metric", "route": "premium_chat", "response_chars": 200},
        ]
        conference_records = [
            {"posted_at": "2026-06-01T10:00:00", "text_markdown": "*Ledger(재무팀)*:\n" + ("가" * 80)},
        ]

        with patch(
            "scripts.summarize_weekly_ops_card.load_recent_fallback_events",
            return_value=[
                {"event_type": "fallback_activated"},
                {"event_type": "fallback_recovered"},
            ],
        ), patch(
            "scripts.summarize_weekly_ops_card._latest_goal_forecast",
            return_value={
                "probability_to_hit": 0.7,
                "recommended_mode": "stay_course",
            },
        ), patch(
            "scripts.summarize_weekly_ops_card._ops_finance_snapshot",
            return_value={
                "runway_days": 900.0,
            },
        ):
            text = _build_slack_summary(route_records, conference_records)

        self.assertIn("CEO weekly ops card", text)
        self.assertIn("route premium share:", text)
        self.assertIn("conference noisy rate:", text)
        self.assertIn("provider incidents: activated 1 / recovered 1 / cleared 0", text)
        self.assertIn("goal forecast:", text)
        self.assertIn("ops runway:", text)

    def test_main_writes_output_file(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            route_path = root / "route.jsonl"
            conference_path = root / "conference.jsonl"
            route_path.write_text(
                json.dumps({"ts": "2026-06-01T10:00:00", "kind": "route", "route": "local_chat", "message": "안녕"}, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
            conference_path.write_text(
                json.dumps({"posted_at": "2026-06-01T10:00:00", "text_markdown": "*Coach(인사팀)*:\n짧은 답"}, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
            output_dir = root / "out"
            old_argv = sys.argv
            try:
                sys.argv = [
                    "summarize_weekly_ops_card.py",
                    "--route-audit-path",
                    str(route_path),
                    "--conference-audit-path",
                    str(conference_path),
                    "--output-dir",
                    str(output_dir),
                    "--date",
                    "2026-06-01",
                ]
                with patch(
                    "scripts.summarize_weekly_ops_card._latest_goal_forecast",
                    return_value={"title": "goal", "probability_to_hit": 0.8, "recommended_mode": "stay_course", "actual_value": 1, "expected_value": 1},
                ), patch(
                    "scripts.summarize_weekly_ops_card._ops_finance_snapshot",
                    return_value={"total_spent_usd": 10.0, "remaining_budget_usd": 6990.0, "avg_daily_burn_usd": 1.0, "runway_days": 6990.0},
                ):
                    rc = main()
            finally:
                sys.argv = old_argv
            self.assertEqual(rc, 0)
            output_path = output_dir / "ceo_weekly_ops_card_2026-06-01.md"
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
