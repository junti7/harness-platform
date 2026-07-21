import json
import unittest
from datetime import datetime as real_datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
import hmac
import hashlib

from adapters.content import openclaw_agent
from adapters.content import tools as openclaw_tools


class OpenClawAgentTests(unittest.TestCase):
    def setUp(self):
        openclaw_agent._CONVERSATION_HISTORY.clear()
        openclaw_agent._rate_buckets.clear()
        self._session_persist_ttl_hours = openclaw_agent.SESSION_PERSIST_TTL_HOURS
        openclaw_agent.SESSION_PERSIST_TTL_HOURS = 0

    def tearDown(self):
        openclaw_agent.SESSION_PERSIST_TTL_HOURS = self._session_persist_ttl_hours

    def test_parse_status_command(self):
        parsed = openclaw_agent._parse_structured_command("status 확인해줘")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "status")
        self.assertEqual(parsed["bridge_args"], ["status", "--format", "text"])

    def test_parse_ar_list_command(self):
        parsed = openclaw_agent._parse_structured_command("AR list 알려주세요.")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "ar-list")
        self.assertEqual(parsed["bridge_args"], ["ar-list", "--format", "text"])

    def test_parse_ar_list_all_command(self):
        parsed = openclaw_agent._parse_structured_command("AR 전체 리스트를 보여줘.")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "ar-list")
        self.assertEqual(parsed["bridge_args"], ["ar-list", "--format", "text", "--all"])

    def test_parse_minutes_status_command(self):
        parsed = openclaw_agent._parse_structured_command("노션 회의록 업로드 상태 확인해줘")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "minutes-status")
        self.assertEqual(parsed["bridge_args"], ["minutes-status", "--format", "text"])

    def test_parse_minutes_upload_proposes_latest_by_default(self):
        parsed = openclaw_agent._parse_structured_command("기존에 있었던 회의 내용을 기반으로 회의록 업로드 해주세요.")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "minutes-latest")
        self.assertEqual(parsed["bridge_args"], ["minutes-latest", "--format", "text"])

    def test_parse_minutes_upload_confirm_executes_upload(self):
        parsed = openclaw_agent._parse_structured_command("회의록 업로드 confirm")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "minutes-upload")
        self.assertEqual(parsed["bridge_args"], ["minutes-upload"])

    def test_parse_minutes_reupload_confirm_executes_reupload(self):
        parsed = openclaw_agent._parse_structured_command("회의록 재업로드 confirm")

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["intent"], "minutes-reupload")
        self.assertEqual(parsed["bridge_args"], ["minutes-reupload"])

    def test_expand_workplace_shorthand_for_ar(self):
        expanded = openclaw_agent._expand_workplace_shorthand("AR list 알려주세요.")

        self.assertIn("AR(Action Required)", expanded)

    def test_chat_prompt_includes_workplace_shorthand_context(self):
        prompt = openclaw_agent._build_chat_system_prompt("AR list 알려주세요.")

        self.assertIn("AR=Action Required", prompt)

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

        self.assertIn("checklist", result)
        self.assertIn("decision card", result)

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

    @patch("adapters.content.openclaw_agent.httpx.post")
    def test_ollama_chat_sends_expanded_workplace_shorthand(self, mock_post):
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {"message": {"content": "ok"}}

        mock_post.return_value = Resp()

        result = openclaw_agent._ollama_chat(
            "http://localhost:11434",
            "test",
            "AR list 알려주세요.",
        )

        self.assertEqual(result, "ok")
        payload = mock_post.call_args.kwargs["json"]
        self.assertIn("AR(Action Required)", payload["messages"][-1]["content"])

    @patch("adapters.content.openclaw_agent._load_status_payload")
    @patch("adapters.content.openclaw_agent._run_ollama_chat")
    @patch("adapters.content.openclaw_agent._run_anthropic_chat")
    def test_top_risk_summary_uses_deterministic_status_brief(self, mock_chat, mock_ollama, mock_status):
        mock_status.return_value = {
            "generated_at": "2026-05-31T10:00:00",
            "runtime": {"slack_phase": "phase1", "capital_actions_enabled": "false"},
            "integrations": {
                "postgres": {"available": False},
                "notion": {"available": True},
                "openclaw": {"available": True},
            },
            "services": {"ollama_11434": True},
        }

        result = openclaw_agent.run("이번 주 top risk 5개와 즉시 조치안을 요약해줘", session_id="ops-session")

        self.assertIn("현재 top risk", result)
        self.assertIn("Postgres unavailable", result)
        self.assertIn("Capital actions remain gated off", result)
        mock_ollama.assert_not_called()
        mock_chat.assert_not_called()

    @patch("adapters.content.openclaw_agent._gmail_get_json")
    @patch("adapters.content.openclaw_agent._gmail_search_json")
    @patch("adapters.content.openclaw_agent._run_ollama_chat")
    @patch("adapters.content.openclaw_agent._run_anthropic_chat")
    def test_mail_lookup_does_not_fetch_bodies(self, mock_chat, mock_ollama, mock_gmail, mock_gmail_get):
        mock_gmail.return_value = {
            "items": [
                {
                    "id": "mail-1",
                    "date": "2026-05-31 09:00",
                    "from": "alerts@example.com",
                    "subject": "Budget warning",
                }
            ],
        }

        result = openclaw_agent.run("최근 온 메일 보여줘", session_id="mail-session")

        self.assertIn("최근 메일 1건", result)
        self.assertIn("Budget warning", result)
        mock_gmail.assert_called_once_with(openclaw_agent._infer_gmail_query("최근 온 메일 보여줘"), limit=5)
        mock_gmail_get.assert_not_called()
        mock_ollama.assert_not_called()
        mock_chat.assert_not_called()

    @patch("adapters.content.openclaw_agent._gmail_get_json")
    @patch("adapters.content.openclaw_agent._gmail_search_json")
    def test_mail_content_summary_requires_and_uses_bodies(self, mock_gmail, mock_gmail_get):
        mock_gmail.return_value = {
            "items": [
                {"id": "mail-1", "from": "ceo@example.com", "subject": "Budget decision"},
                {"id": "mail-2", "from": "googlealerts-noreply@google.com", "subject": "Google 알리미 - AI"},
            ]
        }
        mock_gmail_get.side_effect = [
            {"id": "mail-1", "from": "ceo@example.com", "subject": "Budget decision", "body": "내일까지 예산안을 검토해 승인 여부를 알려주세요."},
            {"id": "mail-2", "from": "googlealerts-noreply@google.com", "subject": "Google 알리미 - 문화", "body": "=== 뉴스 - 다음에 대한 새로운 검색결과 10개: [문화] === 공연 소식입니다."},
        ]

        result = openclaw_agent.run("최근 온 메일 내용 요약해", session_id="mail-summary-session")

        self.assertIn("오늘 확인할 메일이 1건 있습니다.", result)
        self.assertIn("내일까지 예산안을 검토", result)
        self.assertIn("나머지 1건은 업무와 무관한 Google Alerts라 넘겨도 됩니다.", result)
        self.assertEqual(mock_gmail_get.call_count, 2)

    @patch("adapters.content.openclaw_agent._gmail_get_json")
    @patch("adapters.content.openclaw_agent._gmail_search_json")
    def test_mail_summary_returns_explicit_partial_result_when_body_missing(self, mock_gmail, mock_gmail_get):
        mock_gmail.return_value = {"items": [{"id": "mail-1", "from": "alerts@example.com", "subject": "Budget warning"}]}
        mock_gmail_get.return_value = {"ok": False, "error": "Gmail timeout"}

        result = openclaw_agent.run("최근 온 메일 요약해", session_id="mail-partial-session")

        self.assertIn("일부 메일 본문을 불러오지 못해", result)
        self.assertIn("누락된 메일은 판단하지 않았습니다", result)
        self.assertNotIn("Budget warning", result)

    def test_kst_today_filter_uses_message_timestamp_not_gmail_date_syntax(self):
        kst = ZoneInfo("Asia/Seoul")
        window = (real_datetime(2026, 7, 20, 0, 0, tzinfo=kst), real_datetime(2026, 7, 21, 0, 0, tzinfo=kst))
        items = [
            {"id": "today", "date": "2026-07-20 00:01"},
            {"id": "yesterday", "date": "Sun, 19 Jul 2026 23:59:00 +0900"},
            {"id": "unknown", "date": "not-a-date"},
        ]

        filtered = openclaw_agent._filter_gmail_items_to_kst_window(items, window)

        self.assertEqual([item["id"] for item in filtered], ["today"])
        self.assertEqual(openclaw_agent._infer_gmail_query("오늘 온 메일 내용 요약해"), "newer_than:2d")

    def test_gmail_html_css_body_uses_visible_snippet_instead_of_stylesheet(self):
        message = {
            "body": "#outlook a { padding:0; } body { margin:0; } -webkit-text-size-adjust:100%;",
            "snippet": "Claude.ai 보안 로그인 링크가 도착했습니다.",
        }

        result = openclaw_agent._gmail_excerpt(message)

        self.assertIn("Claude.ai 보안 로그인 링크", result)
        self.assertNotIn("#outlook", result)

    def test_gmail_security_summary_does_not_echo_login_link(self):
        result = openclaw_agent._gmail_action_summary(
            {"subject": "Claude.ai의 보안 링크가 도착했습니다"},
            {"from": "no-reply@mail.anthropic.com", "subject": "Claude.ai의 보안 링크가 도착했습니다", "body": "https://example.test/magic-token"},
        )

        self.assertIn("본인이 요청한 경우", result)
        self.assertNotIn("magic-token", result)

    def test_gmail_slack_verification_codes_are_grouped_and_redacted(self):
        items = [
            {"id": "slack-1", "from": "Slack <no-reply@slack.com>", "subject": "Slack 확인 코드: ABC-123"},
            {"id": "slack-2", "from": "Slack <no-reply@slack.com>", "subject": "Slack 확인 코드: DEF-456"},
        ]
        details = {
            "slack-1": {"from": "Slack <no-reply@slack.com>", "subject": "Slack 확인 코드: ABC-123", "body": "확인 코드 ABC-123 https://go.slack.com/secret"},
            "slack-2": {"from": "Slack <no-reply@slack.com>", "subject": "Slack 확인 코드: DEF-456", "body": "확인 코드 DEF-456 https://go.slack.com/secret"},
        }

        with patch("adapters.content.openclaw_agent._gmail_get_json", side_effect=lambda message_id: details[message_id]):
            result = openclaw_agent._render_gmail_brief(items, "newer_than:2d")

        self.assertIn("오늘 확인할 메일이 2건 있습니다.", result)
        self.assertIn("Slack 확인 코드 2건.", result)
        self.assertNotIn("ABC-123", result)
        self.assertNotIn("go.slack.com", result)

    def test_gmail_brief_leads_with_a_human_conclusion_and_discards_noise(self):
        items = [
            {"id": "security", "from": "no-reply@mail.anthropic.com", "subject": "Claude.ai의 보안 링크가 도착했습니다"},
            {"id": "promo", "from": "no-reply@newsletter.example.com", "subject": "Price drop"},
            {"id": "alert-lg", "from": "googlealerts-noreply@google.com", "subject": "Google 알리미 - LG"},
            {"id": "alert-echo", "from": "googlealerts-noreply@google.com", "subject": "Google 알리미 - 에코"},
        ]
        details = {
            "security": {"from": "no-reply@mail.anthropic.com", "subject": "Claude.ai의 보안 링크가 도착했습니다", "body": "로그인 링크"},
            "promo": {"from": "no-reply@newsletter.example.com", "subject": "Price drop", "body": "sale"},
            "alert-lg": {"from": "googlealerts-noreply@google.com", "subject": "Google 알리미 - LG", "body": "=== 뉴스 - 다음에 대한 새로운 검색결과 10개: [LG] === LG전자 흉기난동 협력사 직원 첫 공판 - 연합뉴스"},
            "alert-echo": {"from": "googlealerts-noreply@google.com", "subject": "Google 알리미 - 에코", "body": "=== 뉴스 - 다음에 대한 새로운 검색결과 10개: [에코] === 이펙스 단독 콘서트 성료 - 데일리안"},
        }

        with patch("adapters.content.openclaw_agent._gmail_get_json", side_effect=lambda message_id: details[message_id]):
            result = openclaw_agent._render_gmail_brief(items, "newer_than:2d")

        self.assertIn("오늘 확인할 메일이 1건 있습니다.", result)
        self.assertIn("Claude.ai 로그인 링크 1건. 방금 직접 요청한 경우에만 사용하세요.", result)
        self.assertIn("나머지 3건은 광고·가격 알림과 업무와 무관한 Google Alerts라 넘겨도 됩니다.", result)
        self.assertNotIn("검색 조건", result)
        self.assertNotIn("첫 항목 기준", result)

    def test_gmail_lookup_redacts_url_and_long_token_in_subject(self):
        result = openclaw_agent._render_gmail_lookup(
            [{"date": "2026-07-20", "from": "security@example.com", "subject": "Sign in https://example.test/abc SECRET_TOKEN_12345678901234567890123456789012"}],
            "newer_than:1d",
        )

        self.assertIn("[링크 생략]", result)
        self.assertIn("[토큰 생략]", result)
        self.assertNotIn("example.test", result)

    def test_executive_request_gets_conclusion_first_without_inventing_evidence(self):
        result = openclaw_agent._finalize_response(
            "핵심 리스크는 공급 일정이 불확실하다는 점입니다.",
            "premium_chat",
            "이번 주 리스크를 분석해줘",
        )

        self.assertEqual(result, "결론: 핵심 리스크는 공급 일정이 불확실하다는 점입니다.")

    def test_quality_guard_redacts_secret_and_blocks_rendering_artifact(self):
        secret_result = openclaw_agent._finalize_response(
            "xoxp-secret-token-value-1234567890", "premium_chat", "상태 알려줘"
        )
        artifact_result = openclaw_agent._finalize_response(
            "#outlook a { padding: 0; } -webkit-text-size-adjust: 100%;",
            "premium_chat",
            "내용 요약해줘",
        )

        self.assertIn("[민감 정보 생략]", secret_result)
        self.assertNotIn("secret-token", secret_result)
        self.assertIn("렌더링 조각", artifact_result)

    def test_quality_guard_keeps_markup_when_explicitly_requested(self):
        result = openclaw_agent._finalize_response(
            "body { border-collapse: collapse; }", "premium_chat", "CSS 코드 보여줘"
        )

        self.assertIn("border-collapse", result)

    def test_summary_contract_fails_closed_without_primary_body_evidence(self):
        contract = openclaw_agent._infer_request_contract("오늘 온 메일 내용 요약해")
        verification = openclaw_agent._verify_delivery_contract(
            contract,
            openclaw_agent.EvidenceSet("gmail_metadata", "complete"),
            "deterministic_gmail_lookup",
        )

        self.assertEqual(verification.verdict, "block")

    def test_gmail_alert_signal_checks_only_first_headline(self):
        detail = {
            "subject": "Google 알리미 - LG | 2026-07-20 22:06:46",
            "body": "=== 뉴스 - 다음에 대한 새로운 검색결과 10개: [LG] === LG전자 흉기난동 협력사 직원 첫 공판 - 연합뉴스 이후 AI 반도체 기사",
        }

        self.assertFalse(openclaw_agent._gmail_alert_is_signal(detail))
        self.assertEqual(openclaw_agent._gmail_safe_header_text(detail["subject"]), "Google 알리미 - LG")

    @patch("adapters.content.openclaw_agent._gmail_search_json")
    def test_gmail_runtime_error_does_not_expose_internal_detail(self, mock_gmail):
        mock_gmail.return_value = {"ok": False, "error": "ssh host=secret.internal stack trace"}

        result = openclaw_agent.run("최근 온 메일 내용 요약해", session_id="mail-error-session")

        self.assertIn("Gmail 조회에 실패", result)
        self.assertNotIn("secret.internal", result)

    @patch("adapters.content.openclaw_agent._gmail_get_json")
    @patch("adapters.content.openclaw_agent._gmail_search_json")
    def test_mail_brief_does_not_persist_private_body_excerpt(self, mock_gmail, mock_gmail_get):
        mock_gmail.return_value = {"items": [{"id": "mail-1", "from": "ceo@example.com", "subject": "Private"}]}
        mock_gmail_get.return_value = {"id": "mail-1", "from": "ceo@example.com", "subject": "Private", "body": "private body text"}

        result = openclaw_agent.run("최근 온 메일 내용 요약해", session_id="private-mail-session")

        self.assertIn("private body text", result)
        self.assertEqual(list(openclaw_agent._CONVERSATION_HISTORY["private-mail-session"]), [])

    @patch("adapters.content.openclaw_agent._run_ollama_chat")
    @patch("adapters.content.openclaw_agent.datetime")
    def test_current_time_query_uses_deterministic_response(self, mock_datetime, mock_ollama):
        mock_datetime.now.return_value = real_datetime(2026, 6, 14, 18, 41)

        result = openclaw_agent.run("지금 시각 알려줘", session_id="time-session")

        self.assertEqual(result, "현재 시각은 2026년 06월 14일 18시 41분입니다.")
        mock_ollama.assert_not_called()

    @patch("adapters.content.openclaw_agent._run_ollama_chat")
    def test_greeting_uses_deterministic_response(self, mock_ollama):
        result = openclaw_agent.run("안녕", session_id="greeting-session")

        self.assertEqual(result, "무엇을 도와드릴까요?")
        mock_ollama.assert_not_called()

    def test_log_request_requires_tools(self):
        self.assertTrue(openclaw_agent._needs_tools("백엔드 에러 로그 보여줘"))

    @patch("adapters.content.openclaw_agent._run_anthropic_chat", return_value="fallback")
    @patch("adapters.content.openclaw_agent._ollama_chat", return_value="local-ok")
    @patch("adapters.content.openclaw_agent._ollama_probe", return_value=True)
    @patch("adapters.content.openclaw_agent.should_use_remote_ollama", return_value=False)
    def test_macmini_runtime_skips_remote_ollama_candidate(
        self,
        _mock_should_use_remote,
        _mock_probe,
        mock_ollama_chat,
        _mock_fallback,
    ):
        with patch.object(openclaw_agent, "OLLAMA_REMOTE_HOST", "http://remote-host:11434"), patch.object(
            openclaw_agent, "OLLAMA_HOST", "http://local-host:11434"
        ):
            result = openclaw_agent._run_ollama_chat("안녕")

        self.assertEqual(result, "local-ok")
        mock_ollama_chat.assert_called_once_with(
            "http://local-host:11434",
            "Tier0b/Local-Ollama",
            "안녕",
            history=None,
        )

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

    def test_finalize_response_applies_route_length_cap(self):
        text = "안녕하세요. " + ("가" * 900)

        finalized = openclaw_agent._finalize_response(text, "unknown_route")

        self.assertLessEqual(len(finalized), 700)
        self.assertNotIn("안녕하세요", finalized)

    def test_finalize_response_keeps_sentence_boundary_when_possible(self):
        text = "첫 문장입니다. 둘째 문장도 있습니다. 셋째 문장은 잘려야 합니다."

        finalized = openclaw_agent._finalize_response(text, "economy_chat")

        self.assertIn("첫 문장입니다.", finalized)
        self.assertTrue(finalized.endswith("있습니다.") or finalized.endswith("합니다."))

    def test_run_logs_response_metric_record(self):
        with TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "audit.jsonl"
            with patch.object(openclaw_agent, "ROUTE_AUDIT_PATH", audit_path), patch(
                "adapters.content.openclaw_agent._run_ollama_chat",
                return_value="대표님 이름은 준태입니다.",
            ):
                result = openclaw_agent.run("내 이름이 뭐야?", session_id="metric-session")

            self.assertEqual(result, "대표님 이름은 준태입니다.")
            records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
            metric_records = [record for record in records if record.get("kind") == "response_metric"]
            self.assertTrue(metric_records)
            self.assertEqual(metric_records[-1]["response_chars"], len(result))

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
        self.assertIn("체크리스트", result)

    @patch.dict("os.environ", {"SLACK_CEO_USER_ID": "U_CEO"}, clear=False)
    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    def test_goal_create_requires_authorized_requester(self, _mock_intent):
        result = openclaw_agent.run(
            '/goal create --title "test" --objective "obj" --target-metric free_subscribers --target-value 10 --deadline 2026-06-16',
            requester_user_id="U_OTHER",
        )
        self.assertIn("CEO", result)
        self.assertIn("승인 문안", result)

    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    @patch("adapters.content.openclaw_agent._run_bridge_command", return_value="OK")
    def test_run_routes_structured_command_to_bridge(self, mock_bridge, _mock_intent):
        result = openclaw_agent.run("status 확인해줘")
        self.assertEqual(result, "OK")
        mock_bridge.assert_called_once_with(["status", "--format", "text"])

    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    @patch("adapters.content.openclaw_agent._run_ollama_chat", side_effect=["준태로 기억했습니다.", "대표님 이름은 준태입니다."])
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "auto")
    def test_run_preserves_session_history_for_personal_followups(self, mock_ollama, _mock_intent):
        first = openclaw_agent.run("내 이름은 준태야", session_id="test-session")
        second = openclaw_agent.run("내 이름이 뭐야?", session_id="test-session")

        self.assertEqual(first, "준태로 기억했습니다.")
        self.assertEqual(second, "대표님 이름은 준태입니다.")
        second_call = mock_ollama.call_args_list[1]
        self.assertEqual(second_call.kwargs["history"][0]["content"], "<user_message>내 이름은 준태야</user_message>")
        self.assertEqual(second_call.kwargs["history"][1]["content"], "준태로 기억했습니다.")

    @patch("adapters.content.openclaw_agent._run_ollama_chat", return_value="8")
    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku")
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "auto")
    def test_simple_followup_uses_low_cost_route_without_intent_classifier(self, mock_intent, mock_ollama):
        result = openclaw_agent.run("거기에 4를 곱하면?", session_id="test-session")

        self.assertEqual(result, "8")
        mock_intent.assert_not_called()
        mock_ollama.assert_called_once()

    def test_contextual_followup_is_not_low_cost_candidate(self):
        history = [
            {"role": "user", "content": "<user_message>goal 1 상태 보여줘</user_message>"},
            {"role": "assistant", "content": "goal 1 status ..."},
        ]
        self.assertFalse(openclaw_agent._is_low_cost_chat_candidate("그거 좀 더 자세히", history))

    def test_work_intent_followup_is_not_low_cost_candidate(self):
        history = [
            {"role": "user", "content": "<user_message>오늘 온 메일 보여줘</user_message>"},
            {"role": "assistant", "content": "메일 3건을 확인했습니다."},
        ]
        self.assertFalse(openclaw_agent._is_low_cost_chat_candidate("메일도 같이 확인해줘", history))

    def test_personal_recall_followup_is_low_cost_candidate(self):
        history = [
            {"role": "user", "content": "<user_message>내 이름은 준태야</user_message>"},
            {"role": "assistant", "content": "준태로 기억했습니다."},
        ]
        self.assertTrue(openclaw_agent._is_low_cost_chat_candidate("내 이름이 뭐야?", history))

    def test_analysis_briefing_does_not_require_tools(self):
        self.assertFalse(
            openclaw_agent._needs_tools("지금 진행되고 있는 AI 교육 사업 아이템에 대해 브리핑 해주세요.")
        )

    @patch.dict("os.environ", {"SLACK_CEO_USER_ID": "U_CEO", "SLACK_VP_USER_ID": "U_VP"}, clear=False)
    def test_infer_requester_role(self):
        self.assertEqual(openclaw_agent._infer_requester_role("U_CEO", None), "ceo")
        self.assertEqual(openclaw_agent._infer_requester_role("U_VP", None), "vp")
        self.assertEqual(
            openclaw_agent._infer_requester_role(None, "C0B2TQVV602"),
            "vp",
        )

    def test_contextual_work_followup_preserves_premium_context(self):
        history = [
            {"role": "user", "content": "<user_message>오늘 온 메일 보여줘</user_message>"},
            {"role": "assistant", "content": "최근 메일 3건을 확인했습니다."},
        ]
        risk_scan = {
            "risk_level": "low",
            "flags": [],
            "context_sensitive_terms": ["메일"],
        }
        self.assertTrue(
            openclaw_agent._should_preserve_premium_context(
                "그거 좀 더 자세히 설명해줘",
                history,
                risk_scan,
            )
        )

    def test_analysis_route_does_not_fall_to_local_chat(self):
        route, model = openclaw_agent._select_chat_route(
            user_message="이번 주 top risk 5개와 즉시 조치안을 요약해줘",
            history=[],
            risk_scan={"risk_level": "low", "flags": [], "context_sensitive_terms": []},
            requester_role="ceo",
            chat_backend_mode="auto",
            effective_chat_model=openclaw_agent.OPENCLAW_CHAT_MODEL,
        )
        self.assertEqual((route, model), ("economy_chat", "haiku"))

    def test_vp_review_route_does_not_fall_to_local_chat(self):
        route, model = openclaw_agent._select_chat_route(
            user_message="이 문장 문체가 자연스러운지 봐줘",
            history=[],
            risk_scan={"risk_level": "low", "flags": [], "context_sensitive_terms": []},
            requester_role="vp",
            chat_backend_mode="auto",
            effective_chat_model=openclaw_agent.OPENCLAW_CHAT_MODEL,
        )
        self.assertEqual((route, model), ("economy_chat", "haiku"))

    def test_explicit_file_review_still_requires_tools(self):
        self.assertTrue(
            openclaw_agent._needs_tools("이 파일 읽어보고 브리핑 해줘")
        )

    def test_meeting_summon_does_not_bypass_to_minutes_latest(self):
        self.assertFalse(
            openclaw_agent._should_bypass_minutes_latest(
                "Pretotyping 랜딩 페이지 제작하려면 어떻게 해야할지 논의하기 위한 회의 소집해."
            )
        )

    def test_meeting_status_query_bypasses_to_minutes_latest(self):
        self.assertTrue(
            openclaw_agent._should_bypass_minutes_latest(
                "회의 진행 상황 어떻게 돼?"
            )
        )

    @patch("adapters.content.openclaw_agent._cost_limit_reached", return_value=False)
    def test_briefing_request_skips_haiku_intent_classifier(self, _mock_cost):
        self.assertIsNone(
            openclaw_agent._classify_intent_with_haiku(
                "@friday AI 교육 사업 관련해서 지금까지 진행된 내용을 요약해서 브리핑 하세요."
            )
        )

    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    @patch("adapters.content.openclaw_agent._run_anthropic_chat", return_value="briefing-chat")
    @patch("adapters.content.openclaw_agent._run_tool_agent", return_value="tool-route")
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "anthropic")
    def test_briefing_request_prefers_premium_chat_over_tool_agent(
        self,
        mock_tool,
        mock_chat,
        _mock_intent,
    ):
        result = openclaw_agent.run("지금 진행되고 있는 AI 교육 사업 아이템에 대해 브리핑 해주세요.")

        self.assertEqual(result, "결론: briefing-chat")
        mock_chat.assert_called_once()
        mock_tool.assert_not_called()

    @patch("adapters.content.openclaw_agent._load_status_payload")
    @patch("adapters.content.openclaw_agent._run_haiku_chat")
    @patch("adapters.content.openclaw_agent._run_anthropic_chat")
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "anthropic")
    def test_top_risk_request_uses_deterministic_status_brief_over_haiku(
        self,
        mock_premium,
        mock_haiku,
        mock_status,
    ):
        mock_status.return_value = {
            "generated_at": "2026-05-31T10:00:00",
            "runtime": {"slack_phase": "phase1", "capital_actions_enabled": "false"},
            "integrations": {"postgres": {"available": False}},
            "services": {},
        }

        result = openclaw_agent.run("이번 주 top risk 5개와 즉시 조치안을 요약해줘")

        self.assertIn("현재 top risk", result)
        mock_haiku.assert_not_called()
        mock_premium.assert_not_called()

    @patch.dict("os.environ", {"SLACK_VP_USER_ID": "U_VP"}, clear=False)
    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    @patch("adapters.content.openclaw_agent._run_haiku_chat", return_value="vp-economy")
    @patch("adapters.content.openclaw_agent._run_anthropic_chat", return_value="premium-chat")
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "anthropic")
    def test_vp_review_request_uses_haiku_when_low_risk(
        self,
        mock_premium,
        mock_haiku,
        _mock_intent,
    ):
        result = openclaw_agent.run(
            "이 문장 문체가 자연스러운지 봐줘",
            requester_user_id="U_VP",
        )

        self.assertEqual(result, "vp-economy")
        mock_haiku.assert_called_once()
        mock_premium.assert_not_called()

    @patch("adapters.content.openclaw_agent._classify_intent_with_haiku", return_value=None)
    @patch("adapters.content.openclaw_agent._run_haiku_chat", return_value="economy-chat")
    @patch("adapters.content.openclaw_agent._run_anthropic_chat", return_value="premium-context")
    @patch.object(openclaw_agent, "OPENCLAW_CHAT_BACKEND", "anthropic")
    def test_contextual_followup_stays_on_premium_even_if_low_risk(
        self,
        mock_premium,
        mock_haiku,
        _mock_intent,
    ):
        openclaw_agent._record_conversation_turn(
            "mail-session",
            "오늘 온 메일 보여줘",
            "최근 메일 3건을 확인했습니다.",
        )

        result = openclaw_agent.run("그거 좀 더 자세히 설명해줘", session_id="mail-session")

        self.assertEqual(result, "premium-context")
        mock_premium.assert_called_once()
        mock_haiku.assert_not_called()

    @patch.dict("os.environ", {"OPENCLAW_WEB_SEARCH_PROVIDER": "brave", "BRAVE_SEARCH_API_KEY": "test-key"}, clear=False)
    @patch("adapters.content.tools.httpx.get")
    def test_web_search_brave_formats_results(self, mock_get):
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "web": {
                        "results": [
                            {
                                "title": "Result A",
                                "url": "https://example.com/a",
                                "description": "Snippet A",
                                "page_age": "May 22, 2026",
                            }
                        ]
                    }
                }

        mock_get.return_value = Resp()

        result = openclaw_tools.tool_web_search("physical ai", count=3)

        self.assertIn("provider: brave", result)
        self.assertIn("Result A", result)
        self.assertIn("https://example.com/a", result)
        self.assertIn("게시일: May 22, 2026", result)
        mock_get.assert_called_once()

    @patch.dict("os.environ", {"OPENCLAW_WEB_SEARCH_PROVIDER": "duckduckgo", "BRAVE_SEARCH_API_KEY": ""}, clear=False)
    @patch("adapters.content.tools.httpx.get")
    def test_web_search_duckduckgo_formats_results(self, mock_get):
        class Resp:
            text = """
            <div class="result">
              <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fb">Result B</a>
              <a class="result__snippet">Snippet B</a>
            </div>
            """

            def raise_for_status(self):
                return None

        mock_get.return_value = Resp()

        result = openclaw_tools.tool_web_search("physical ai", count=3)

        self.assertIn("provider: duckduckgo_html", result)
        self.assertIn("Result B", result)
        self.assertIn("https://example.com/b", result)
        self.assertIn("게시일: 미확인", result)

    def test_recency_sensitive_tool_prompt_requires_dates(self):
        prompt = openclaw_agent._build_tool_system_prompt("Physical AI robotics 최신 뉴스 검색해주세요")

        self.assertIn("Recency-sensitive query rule", prompt)
        self.assertIn("게시일: 미확인", prompt)

    def test_browser_research_blocks_purchase_actions(self):
        result = openclaw_tools.tool_browser_research(
            task="쿠팡에서 제일 싼 제품 구매해줘",
            query="USB C 케이블",
            site="coupang",
        )

        self.assertIn("browser_research 차단", result)
        self.assertIn("구매", result)

    @patch("adapters.content.tools.subprocess.run")
    def test_browser_research_runs_read_only_script(self, mock_run):
        class Result:
            returncode = 0
            stdout = "✅ 브라우저 read-only 검색 완료"
            stderr = ""

        mock_run.return_value = Result()

        result = openclaw_tools.tool_browser_research(
            task="쿠팡에서 공개 검색 결과 가격 비교",
            query="USB C 케이블",
            site="coupang",
            max_items=3,
        )

        self.assertIn("read-only", result)
        cmd = mock_run.call_args.args[0]
        self.assertIn("scripts/browser_research.py", cmd[1])
        self.assertIn("--site", cmd)
        self.assertIn("coupang", cmd)

    @patch.dict(
        "os.environ",
        {
            "COUPANG_PARTNERS_ACCESS_KEY": "access-key",
            "COUPANG_PARTNERS_SECRET_KEY": "secret-key",
        },
        clear=False,
    )
    @patch("adapters.content.tools.datetime")
    def test_coupang_hmac_headers_format(self, mock_datetime):
        mock_datetime.utcnow.return_value.strftime.return_value = "260522T101112Z"

        headers = openclaw_tools._coupang_hmac_headers(
            "GET",
            "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search?keyword=usb&limit=3",
        )

        expected = hmac.new(
            b"secret-key",
            b"260522T101112ZGET/v2/providers/affiliate_open_api/apis/openapi/v1/products/searchkeyword=usb&limit=3",
            hashlib.sha256,
        ).hexdigest()
        self.assertIn(expected, headers["Authorization"])
        self.assertIn("access-key=access-key", headers["Authorization"])

    @patch.dict(
        "os.environ",
        {
            "COUPANG_PARTNERS_ACCESS_KEY": "",
            "COUPANG_PARTNERS_SECRET_KEY": "",
        },
        clear=False,
    )
    def test_coupang_product_search_requires_credentials(self):
        result = openclaw_tools.tool_coupang_product_search("USB C 케이블", 3)

        self.assertIn("COUPANG_PARTNERS_ACCESS_KEY", result)

    @patch.dict(
        "os.environ",
        {
            "COUPANG_PARTNERS_ACCESS_KEY": "access-key",
            "COUPANG_PARTNERS_SECRET_KEY": "secret-key",
        },
        clear=False,
    )
    @patch("adapters.content.tools.httpx.get")
    @patch("adapters.content.tools.datetime")
    def test_coupang_product_search_formats_response(self, mock_datetime, mock_get):
        mock_datetime.utcnow.return_value.strftime.return_value = "260522T101112Z"

        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "data": {
                        "productData": [
                            {
                                "productName": "USB C 케이블 1m",
                                "productPrice": 4900,
                                "productUrl": "https://link.coupang.com/a/test",
                            }
                        ]
                    }
                }

        mock_get.return_value = Resp()

        result = openclaw_tools.tool_coupang_product_search("USB C 케이블", 3)

        self.assertIn("쿠팡 파트너스 API 상품 검색 완료", result)
        self.assertIn("4,900원", result)
        self.assertIn("https://link.coupang.com/a/test", result)


if __name__ == "__main__":
    unittest.main()
