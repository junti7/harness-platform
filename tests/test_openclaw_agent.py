import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path

from adapters.content import openclaw_agent


class OpenClawAgentTests(unittest.TestCase):
    def setUp(self):
        openclaw_agent._CONVERSATION_HISTORY.clear()

    def test_parse_status_command(self):
        parsed = openclaw_agent._parse_structured_command("status 확인해줘")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "status")
        self.assertEqual(parsed["bridge_args"], ["status", "--format", "text"])

    def test_arithmetic_followup_is_deterministic(self):
        first = openclaw_agent.run("1+1=?", session_id="math-session")
        second = openclaw_agent.run("거기에 3을 나누면?", session_id="math-session")

        self.assertEqual(first, "2")
        self.assertEqual(second, "0.6666666667")

    def test_rolling_context_blocks_ambiguous_publish_followup(self):
        openclaw_agent._record_conversation_turn(
            "risk-session",
            "뉴스레터 초안 준비됐어?",
            "Physical AI Weekly 초안이 준비됐습니다.",
        )

        result = openclaw_agent.run("그거 보내줘", session_id="risk-session", requester_user_id="U_CEO")

        self.assertIn("민감한 대상", result)

    def test_bridge_preflight_uses_action_registry(self):
        result = openclaw_agent._preflight_bridge_command(
            ["run-pipeline"],
            requester_user_id=None,
            risk_scan={"risk_level": "low", "flags": []},
        )

        self.assertIn("CEO", result)

    def test_tool_preflight_blocks_contextual_high_risk_reference(self):
        risk_scan = {
            "risk_level": "high",
            "flags": ["contextual_high_risk_reference"],
            "context_sensitive_terms": ["초안", "substack"],
        }
        result = openclaw_agent._preflight_tool_call("send_slack", "U_CEO", risk_scan)

        self.assertIn("민감한 대상", result)

    @patch("adapters.content.openclaw_agent._run_tool_agent")
    def test_newsletter_draft_status_is_deterministic(self, mock_tool):
        result = openclaw_agent.run("뉴스레터 초안 준비됐어?", session_id="newsletter-session")

        self.assertIn("확인된 뉴스레터 초안은 있습니다", result)
        self.assertIn("docs/issues/physical_ai_weekly_001_2026-05-10.md", result)
        self.assertNotIn("대통령", result)
        mock_tool.assert_not_called()

    @patch("adapters.content.openclaw_agent._run_ollama_chat")
    @patch("adapters.content.openclaw_agent._run_anthropic_chat", return_value="premium-route")
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "auto")
    def test_high_risk_terms_do_not_fall_to_local_llm(self, mock_chat, mock_ollama):
        result = openclaw_agent.run("가격 바꿀까?", session_id="risk-session")

        self.assertEqual(result, "premium-route")
        mock_ollama.assert_not_called()
        mock_chat.assert_called_once()

    def test_route_audit_records_blocked_contextual_risk(self):
        with TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit.jsonl"
            with patch.object(openclaw_agent, "ROUTE_AUDIT_PATH", audit_path):
                openclaw_agent._record_conversation_turn(
                    "audit-session",
                    "보고서 초안 준비됐어?",
                    "보고서 초안이 준비됐습니다.",
                )
                result = openclaw_agent.run("그거 보내줘", session_id="audit-session")

            self.assertIn("민감한 대상", result)
            log_text = audit_path.read_text(encoding="utf-8")
            self.assertIn('"route": "contextual_risk_block"', log_text)
            self.assertIn('"blocked": true', log_text)

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
    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    def test_mutating_command_requires_authorized_requester(self, _mock_intent):
        result = openclaw_agent.run(
            "파이프라인 실행해줘",
            requester_user_id="U_OTHER",
        )
        self.assertIn("CEO", result)

    @patch.dict("os.environ", {"SLACK_CEO_USER_ID": "U_CEO"}, clear=False)
    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    def test_goal_create_requires_authorized_requester(self, _mock_intent):
        result = openclaw_agent.run(
            '/goal create --title "test" --objective "obj" --target-metric free_subscribers --target-value 10 --deadline 2026-06-16',
            requester_user_id="U_OTHER",
        )
        self.assertIn("CEO", result)

    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    @patch("adapters.content.openclaw_agent._run_bridge_command", return_value="OK")
    def test_run_routes_structured_command_to_bridge(self, mock_bridge, _mock_intent):
        result = openclaw_agent.run("status 확인해줘")
        self.assertEqual(result, "OK")
        mock_bridge.assert_called_once_with(["status", "--format", "text"])

    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    @patch("adapters.content.openclaw_agent._needs_tools", return_value=False)
    @patch("adapters.content.openclaw_agent._run_anthropic_chat", side_effect=["2", "8"])
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "sonnet")
    def test_run_preserves_session_history_for_followups(self, mock_chat, _mock_needs, _mock_intent):
        first = openclaw_agent.run("내 이름은 준태야", session_id="test-session")
        second = openclaw_agent.run("내 이름이 뭐야?", session_id="test-session")

        self.assertEqual(first, "2")
        self.assertEqual(second, "8")
        second_call = mock_chat.call_args_list[1]
        self.assertEqual(second_call.kwargs["history"][0]["content"], "<user_message>내 이름은 준태야</user_message>")
        self.assertEqual(second_call.kwargs["history"][1]["content"], "2")

    @patch("adapters.content.openclaw_agent._run_ollama_chat", return_value="8")
    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku")
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "auto")
    def test_simple_followup_uses_low_cost_route_without_intent_classifier(self, mock_intent, mock_ollama):
        result = openclaw_agent.run("거기에 4를 곱하면?", session_id="test-session")

        self.assertEqual(result, "8")
        mock_intent.assert_not_called()
        mock_ollama.assert_called_once()


if __name__ == "__main__":
    unittest.main()
