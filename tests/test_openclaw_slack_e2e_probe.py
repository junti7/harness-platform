import importlib.util
from pathlib import Path
import unittest


_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "openclaw_slack_e2e_probe.py"
_SPEC = importlib.util.spec_from_file_location("openclaw_slack_e2e_probe", _SCRIPT)
probe = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(probe)


class OpenClawSlackE2EProbeTests(unittest.TestCase):
    def test_reply_selection_skips_async_processing_ack(self):
        messages = [
            {"ts": "100.1", "user": "U_BOT", "bot_id": "B_BOT", "text": ":thinking_face: 처리 중... (잠시 기다려주세요)"},
            {"ts": "101.1", "user": "U_BOT", "bot_id": "B_BOT", "text": "오늘은 업무상 처리할 메일이 없습니다."},
        ]

        reply = probe._find_bot_reply(messages, "U_BOT", 100.0)

        self.assertEqual(reply["text"], "오늘은 업무상 처리할 메일이 없습니다.")
