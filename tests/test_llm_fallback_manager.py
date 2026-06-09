import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import llm_fallback_manager


class LlmFallbackManagerTests(unittest.TestCase):
    def test_record_fallback_notifies_once_within_cooldown(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "persona_llm_fallback.json"
            with patch.object(llm_fallback_manager, "FALLBACK_STATE_PATH", path), patch.object(
                llm_fallback_manager, "send_slack_route"
            ) as mock_send:
                llm_fallback_manager.record_fallback("friday", "claude", "gemini", "usage_limit_exceeded")
                llm_fallback_manager.record_fallback("friday", "claude", "gemini", "usage_limit_exceeded")

            self.assertEqual(mock_send.call_count, 1)
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(state["friday"]["current_provider"], "gemini")

    def test_clear_fallback_notifies_recovery(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "persona_llm_fallback.json"
            path.write_text(
                json.dumps(
                    {
                        "friday": {
                            "primary_provider": "claude",
                            "current_provider": "gemini",
                            "switched_at": "2026-06-01T00:00:00+00:00",
                            "reason": "usage_limit_exceeded",
                            "last_retry": "2026-06-01T00:00:00+00:00",
                        }
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(llm_fallback_manager, "FALLBACK_STATE_PATH", path), patch.object(
                llm_fallback_manager, "send_slack_route"
            ) as mock_send:
                llm_fallback_manager.clear_fallback("friday")

            self.assertEqual(mock_send.call_count, 1)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {})

    def test_load_recent_fallback_events_returns_latest_first(self):
        with TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "persona_llm_fallback.json"
            events_path = Path(tmpdir) / "persona_llm_fallback_events.jsonl"
            events_path.write_text(
                "\n".join(
                    [
                        json.dumps({"ts": "2026-06-01T00:00:00+00:00", "persona_display": "A", "event_type": "fallback_activated"}),
                        json.dumps({"ts": "2026-06-01T00:01:00+00:00", "persona_display": "B", "event_type": "fallback_recovered"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            with patch.object(llm_fallback_manager, "FALLBACK_STATE_PATH", state_path), patch.object(
                llm_fallback_manager, "FALLBACK_EVENTS_PATH", events_path
            ):
                events = llm_fallback_manager.load_recent_fallback_events(limit=10)

            self.assertEqual(len(events), 2)
            self.assertEqual(events[0]["persona_display"], "B")
            self.assertEqual(events[1]["persona_display"], "A")


if __name__ == "__main__":
    unittest.main()
