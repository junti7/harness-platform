import unittest
from unittest.mock import patch

from adapters.content import openclaw_agent


class OpenClawAgentTests(unittest.TestCase):
    def test_parse_status_command(self):
        parsed = openclaw_agent._parse_structured_command("status 확인해줘")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "status")
        self.assertEqual(parsed["bridge_args"], ["status", "--format", "text"])

    def test_parse_goal_cli_status_command(self):
        parsed = openclaw_agent._parse_structured_command("/goal status 3")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "goal-status")
        self.assertEqual(parsed["bridge_args"], ["goal-status", "3"])

    def test_parse_goal_cli_substack_snapshot_command(self):
        parsed = openclaw_agent._parse_structured_command(
            "/goal substack-snapshot 3 --expected-value 6 --forecast-probability 0.42 --followers 120"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "goal-substack-snapshot")
        self.assertEqual(
            parsed["bridge_args"],
            [
                "goal-substack-snapshot",
                "3",
                "--expected-value",
                "6",
                "--forecast-probability",
                "0.42",
                "--followers",
                "120",
            ],
        )

    def test_parse_goal_cli_provider_snapshot_command(self):
        parsed = openclaw_agent._parse_structured_command(
            "/goal provider-snapshot 3 --provider substack --expected-value 6 --forecast-probability 0.42"
        )
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "goal-provider-snapshot")
        self.assertEqual(
            parsed["bridge_args"],
            [
                "goal-provider-snapshot",
                "3",
                "--provider",
                "substack",
                "--expected-value",
                "6",
                "--forecast-probability",
                "0.42",
            ],
        )

    def test_parse_goal_natural_language_diagnose_command(self):
        parsed = openclaw_agent._parse_structured_command("goal 7 진단해줘")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "goal-diagnose")
        self.assertEqual(parsed["bridge_args"], ["goal-diagnose", "7", "--format", "text"])

    def test_parse_decision_card_command(self):
        parsed = openclaw_agent._parse_structured_command("research_report 7 decision card 보여줘")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "decision-card")
        self.assertEqual(
            parsed["bridge_args"],
            ["decision-card", "research_report", "7", "--format", "text"],
        )

    def test_parse_approval_missing_fields(self):
        parsed = openclaw_agent._parse_structured_command("refined_output 3 승인 기록해줘")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "record-decision-missing-fields")
        self.assertIn("approval_type", parsed["error"])

    def test_parse_approval_command(self):
        message = (
            "refined_output 3 승인 기록해줘 "
            "approval_type: report_publish_approve decision: approved reason: mobile approve"
        )
        parsed = openclaw_agent._parse_structured_command(message)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "record-decision")
        self.assertEqual(
            parsed["bridge_args"],
            [
                "record-decision",
                "refined_output",
                "3",
                "approved",
                "report_publish_approve",
                "--reason",
                "mobile approve",
            ],
        )

    def test_status_keyword_inside_pipeline_sentence_does_not_trigger_status_intent(self):
        parsed = openclaw_agent._parse_structured_command(
            "pipeline 상태 이상하면 ops-incidents에 알려줘"
        )
        self.assertIsNone(parsed)

    @patch(
        "adapters.content.openclaw_agent._parse_failure_memory",
        return_value=[
            {
                "id": "FM-001 Status Intent Miss",
                "input_text": "status 확인해줘",
                "wrong_behavior": "ask unnecessary clarification",
                "expected_behavior": "run bridge status",
                "root_cause": "missed intent",
                "fix_rule": "route status to bridge",
                "trigger_patterns": ["status", "상태"],
            }
        ],
    )
    def test_retrieve_failure_memory_for_status(self, _mock_parse):
        entries = openclaw_agent._retrieve_failure_memories("status 확인해줘")
        self.assertTrue(entries)
        self.assertEqual(entries[0]["id"], "FM-001 Status Intent Miss")

    @patch.dict("os.environ", {"SLACK_CEO_USER_ID": "U_CEO"}, clear=False)
    def test_mutating_command_requires_authorized_requester(self):
        result = openclaw_agent.run(
            "파이프라인 실행해줘",
            requester_user_id="U_OTHER",
        )
        self.assertIn("CEO", result)

    @patch.dict("os.environ", {"SLACK_CEO_USER_ID": "U_CEO"}, clear=False)
    def test_goal_create_requires_authorized_requester(self):
        result = openclaw_agent.run(
            '/goal create --title "test" --objective "obj" --target-metric free_subscribers --target-value 10 --deadline 2026-06-16',
            requester_user_id="U_OTHER",
        )
        self.assertIn("CEO", result)

    @patch("adapters.content.openclaw_agent._run_bridge_command", return_value="OK")
    def test_run_routes_structured_command_to_bridge(self, mock_bridge):
        result = openclaw_agent.run("status 확인해줘")
        self.assertEqual(result, "OK")
        mock_bridge.assert_called_once_with(["status", "--format", "text"])


if __name__ == "__main__":
    unittest.main()
