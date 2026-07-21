import unittest
from unittest.mock import patch

from adapters.content import slack_listener
from core.openclaw_response_quality import DeliveryDecision, SCHEMA_VERSION, VerifiedText


class SlackListenerDmEventTests(unittest.TestCase):
    def test_verified_text_without_system_reason_does_not_crash(self):
        verified = VerifiedText(DeliveryDecision(SCHEMA_VERSION, "deliver", "검증됨"))

        self.assertEqual(slack_listener._outbound_text(verified), "검증됨")

    @patch.object(slack_listener, "CEO_SLACK_USER_ID", "U_CEO")
    def test_ceo_user_token_probe_with_bot_id_is_accepted(self):
        event = {"user": "U_CEO", "bot_id": "B_APP", "app_id": "A_APP"}

        self.assertFalse(slack_listener._should_ignore_dm_event(event))

    @patch.object(slack_listener, "CEO_SLACK_USER_ID", "U_CEO")
    def test_real_bot_and_non_ceo_bot_tagged_events_remain_ignored(self):
        self.assertTrue(slack_listener._should_ignore_dm_event({"user": "U_BOT", "bot_id": "B_APP"}))
        self.assertTrue(slack_listener._should_ignore_dm_event({"user": "U_OTHER", "bot_id": "B_APP"}))

    @patch.object(slack_listener, "CEO_SLACK_USER_ID", "U_CEO")
    def test_subtype_event_remains_ignored_even_if_ceo(self):
        self.assertTrue(slack_listener._should_ignore_dm_event({"user": "U_CEO", "subtype": "message_changed"}))
