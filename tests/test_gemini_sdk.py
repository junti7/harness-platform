import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core import gemini_sdk


class GeminiSdkFallbackTest(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "GEMINI_LOCAL_FALLBACK_ENABLED": "true",
            "OLLAMA_HOST": "http://localhost:11434",
            "GEMINI_LOCAL_FALLBACK_MODEL": "gemma4:latest",
        },
        clear=False,
    )
    @patch("core.gemini_sdk.httpx.post")
    @patch("core.gemini_sdk.httpx.get")
    @patch("core.gemini_sdk.build_client")
    def test_generate_text_falls_back_to_ollama_json(
        self,
        mock_build_client: Mock,
        mock_get: Mock,
        mock_post: Mock,
    ) -> None:
        broken_client = Mock()
        broken_client.models.generate_content.side_effect = RuntimeError("quota exceeded")
        mock_build_client.return_value = broken_client
        mock_get.return_value = SimpleNamespace(status_code=200)
        mock_post.return_value = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"message": {"content": '{"ok": true}'}},
        )

        meta: dict[str, str] = {}
        text, usage = gemini_sdk.generate_text(
            "prompt",
            model="gemini-2.5-flash",
            response_mime_type="application/json",
            meta=meta,
        )

        self.assertEqual(text, '{"ok": true}')
        self.assertEqual(usage["prompt_token_count"], 0)
        self.assertEqual(meta["provider"], "ollama")
        self.assertEqual(meta["model"], "gemma4:latest")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["format"], "json")
        self.assertEqual(payload["model"], "gemma4:latest")

    @patch.dict(os.environ, {"GEMINI_LOCAL_FALLBACK_ENABLED": "false"}, clear=False)
    @patch("core.gemini_sdk.build_client")
    def test_generate_text_raises_when_local_fallback_disabled(self, mock_build_client: Mock) -> None:
        broken_client = Mock()
        broken_client.models.generate_content.side_effect = RuntimeError("quota exceeded")
        mock_build_client.return_value = broken_client

        with self.assertRaises(RuntimeError):
            gemini_sdk.generate_text("prompt", model="gemini-2.5-flash")


if __name__ == "__main__":
    unittest.main()
