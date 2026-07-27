import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core import kimi_shadow


class KimiShadowTests(unittest.TestCase):
    @patch.dict(os.environ, {"KIMI_API_KEY": "test-key", "KIMI_SHADOW_MODEL": "k3-256k"}, clear=False)
    @patch("core.kimi_shadow.httpx.post")
    def test_run_kimi_shadow_eval_records_privacy_safe_metrics(self, mock_post):
        mock_post.return_value = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [{"message": {"content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 3},
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "shadow.jsonl"
            record = kimi_shadow.run_kimi_shadow_eval(
                source="test",
                prompt="return json",
                baseline_provider="ollama",
                baseline_model="qwen",
                baseline_response='{"ok": false}',
                response_mime_type="application/json",
                output_path=output,
            )
            saved = json.loads(output.read_text(encoding="utf-8"))

        self.assertTrue(record["ok"])
        self.assertTrue(saved["json_valid"])
        self.assertEqual(saved["provider"], "kimi")
        self.assertEqual(saved["model"], "k3-256k")
        self.assertNotIn("prompt", saved)
        self.assertNotIn("response", saved)
        self.assertEqual(saved["prompt_token_count"], 12)
        self.assertEqual(saved["candidates_token_count"], 3)

    @patch.dict(os.environ, {"KIMI_SHADOW_EVAL_ENABLED": "false", "KIMI_API_KEY": "test-key"}, clear=False)
    def test_submit_returns_false_when_disabled(self):
        submitted = kimi_shadow.submit_kimi_shadow_eval(
            source="test",
            prompt="hello",
            baseline_provider="ollama",
            baseline_model="qwen",
        )

        self.assertFalse(submitted)


if __name__ == "__main__":
    unittest.main()
