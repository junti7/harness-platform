import unittest
from datetime import date, datetime
from unittest.mock import Mock, patch

from scripts import run_goal_snapshot


class RunGoalSnapshotTests(unittest.TestCase):
    def test_pace_forecast_computes_expected_probability_and_health(self):
        goal = {
            "baseline_value": 0,
            "target_value": 50,
            "unit": "subscribers",
            "created_at": datetime(2026, 5, 1),
            "deadline": datetime(2026, 5, 31),
        }

        expected, probability, health, note = run_goal_snapshot._pace_forecast(
            goal, actual_value=20, today=date(2026, 5, 16)
        )

        self.assertEqual(expected, 25.0)
        self.assertEqual(probability, 0.8)
        self.assertEqual(health, "yellow")
        self.assertIn("pace_model=linear", note)

    def test_pace_forecast_uses_warmup_mode_for_first_two_days(self):
        goal = {
            "baseline_value": 0,
            "target_value": 50,
            "unit": "subscribers",
            "created_at": datetime(2026, 5, 30),
            "deadline": datetime(2026, 6, 29),
        }

        expected, probability, health, note = run_goal_snapshot._pace_forecast(
            goal, actual_value=0, today=date(2026, 5, 30)
        )

        self.assertEqual(expected, 0.0)
        self.assertEqual(probability, 0.5)
        self.assertEqual(health, "green")
        self.assertIn("pace_model=warmup", note)

    def test_record_active_goal_snapshots_records_supported_goal(self):
        goal = {
            "id": 3,
            "target_metric": "free_subscribers",
            "baseline_value": 0,
            "target_value": 50,
            "created_at": datetime(2026, 5, 1),
            "deadline": datetime(2026, 5, 31),
            "channel": "substack",
            "metadata": {"provider": "substack"},
        }
        adapter = Mock()
        adapter.fetch_metrics.return_value = {"free_subscribers": 12, "paid_subscribers": 1}
        adapter.build_components.return_value = [{"component_name": "free_subscribers"}]

        with patch.object(run_goal_snapshot, "_active_goals", return_value=[goal]), patch.object(
            run_goal_snapshot.provider_registry, "get", return_value=adapter
        ), patch.object(
            run_goal_snapshot, "_hydrate_missing_metrics", side_effect=lambda provider_name, metrics: metrics
        ), patch.object(
            run_goal_snapshot, "record_goal_snapshot", return_value={"goal_id": 3, "id": 10}
        ) as mock_record:
            result = run_goal_snapshot.record_active_goal_snapshots(today=date(2026, 5, 16))

        self.assertEqual(result, [{"goal_id": 3, "id": 10}])
        self.assertEqual(mock_record.call_args.kwargs["actual_value"], 12.0)
        self.assertEqual(mock_record.call_args.kwargs["snapshot_date"], "2026-05-16")

    def test_hydrate_missing_metrics_from_db_snapshot(self):
        with patch.object(
            run_goal_snapshot,
            "_latest_subscriber_snapshot",
            return_value={"free_subscribers": 9, "paid_subscribers": 2},
        ):
            hydrated = run_goal_snapshot._hydrate_missing_metrics(
                "substack",
                {"free_subscribers": None, "paid_subscribers": None, "post_count": 3},
            )

        self.assertEqual(hydrated["free_subscribers"], 9)
        self.assertEqual(hydrated["paid_subscribers"], 2)
        self.assertEqual(hydrated["post_count"], 3)


if __name__ == "__main__":
    unittest.main()
