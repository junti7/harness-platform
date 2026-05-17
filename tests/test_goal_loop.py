import unittest
from unittest.mock import patch

from scripts import goal_loop


class GoalLoopTests(unittest.TestCase):
    @patch("scripts.goal_loop.execute_query")
    def test_get_goal_status_aggregates_latest_records(self, mock_execute_query):
        mock_execute_query.side_effect = [
            [{"id": 3, "title": "Goal", "status": "active", "target_metric": "free_subscribers", "target_value": 10, "current_value": 4, "deadline": "2026-06-16"}],
            [{"id": 11, "goal_id": 3, "model_type": "deterministic_funnel", "version": 2, "trigger_thresholds": {"escalate_probability_below": 0.4}}],
            [{"id": 21, "goal_id": 3, "health_status": "yellow", "variance": -2.0}],
            [{"id": 31, "goal_id": 3, "probability_to_hit": 0.42, "recommended_mode": "local_revision"}],
            [{"id": 41, "goal_id": 3, "root_cause_hypothesis": "CTR shortfall", "component_name": "ctr"}],
            [{"unresolved_count": 2}],
        ]

        payload = goal_loop.get_goal_status(3)

        self.assertEqual(payload["goal"]["id"], 3)
        self.assertEqual(payload["active_model"]["version"], 2)
        self.assertEqual(payload["latest_forecast"]["recommended_mode"], "local_revision")
        self.assertEqual(payload["unresolved_anomalies"], 2)

    @patch("scripts.goal_loop.execute_query")
    def test_diagnose_goal_uses_worst_component_and_feedback(self, mock_execute_query):
        mock_execute_query.side_effect = [
            [{"id": 3, "title": "Goal", "status": "active", "target_metric": "free_subscribers", "target_value": 10, "current_value": 4, "deadline": "2026-06-16"}],
            [{"id": 11, "goal_id": 3, "model_type": "deterministic_funnel", "version": 2, "trigger_thresholds": {"escalate_probability_below": 0.4}}],
            [{"id": 21, "goal_id": 3, "health_status": "red", "actual_value": 4, "expected_value": 7, "variance": -3.0}],
            [{"id": 31, "goal_id": 3, "probability_to_hit": 0.31, "recommended_mode": "escalate"}],
            [],
            [{"unresolved_count": 1}],
            [
                {"id": 101, "component_name": "ctr", "expected_value": 0.05, "actual_value": 0.02, "variance": -0.03},
                {"id": 102, "component_name": "cvr", "expected_value": 0.2, "actual_value": 0.18, "variance": -0.02},
            ],
            [{"source_type": "vp_review", "signal_type": "headline_confusing", "signal_text": "제목이 너무 기술자 중심", "severity": "medium"}],
            [{"id": 501, "goal_id": 3, "diagnosis_type": "component_underperformance", "root_cause_hypothesis": "stub", "executive_escalation_required": True}],
        ]

        result = goal_loop.diagnose_goal(3)

        self.assertEqual(result["primary_component"]["component_name"], "ctr")
        self.assertTrue(result["executive_escalation_required"])
        self.assertIn("vp_review:headline_confusing", result["root_cause_hypothesis"])

    @patch("scripts.goal_loop.record_goal_snapshot")
    def test_record_substack_goal_snapshot_builds_metrics_payload(self, mock_record_goal_snapshot):
        mock_record_goal_snapshot.return_value = {"id": 1}

        goal_loop.record_substack_goal_snapshot(
            goal_id=3,
            actual_value=None,
            expected_value=8.0,
            forecast_probability=0.55,
            metrics={"free_subscribers": 5, "paid_subscribers": 0},
            follower_count=120,
            recommendation_subscribers=2,
            direct_subscribers=3,
            welcome_page_visitors=80,
            welcome_page_conversion_rate=0.06,
            note_publish_count=4,
        )

        kwargs = mock_record_goal_snapshot.call_args.kwargs
        self.assertEqual(kwargs["actual_value"], 5.0)
        self.assertIn("followers", kwargs["source_metrics_json"])
        self.assertIn("recommendation_subscribers", kwargs["source_metrics_json"])
        self.assertIn("welcome_page_conversion_rate", kwargs["source_metrics_json"])
        self.assertIn("note_publish_count", kwargs["components_json"])


if __name__ == "__main__":
    unittest.main()
