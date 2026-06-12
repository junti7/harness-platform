import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core import embeddings


class EmbeddingsFallbackTest(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "EMBEDDING_PROVIDER_MODE": "auto",
            "GOOGLE_API_KEY": "",
            "OLLAMA_HOST": "http://localhost:11434",
            "OLLAMA_EMBED_MODEL": "nomic-embed-text",
            "OLLAMA_EMBED_DIM": "4",
        },
        clear=False,
    )
    @patch("core.embeddings.httpx.post")
    @patch("core.embeddings.httpx.get")
    def test_embed_query_uses_ollama_when_google_unavailable(
        self,
        mock_get: Mock,
        mock_post: Mock,
    ) -> None:
        mock_get.return_value = SimpleNamespace(status_code=200)
        mock_post.return_value = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"embeddings": [[0.1, 0.2, 0.3, 0.4]]},
        )

        with patch.object(embeddings, "_OLLAMA_EMBED_MODEL", "nomic-embed-text"), patch.object(
            embeddings, "_OLLAMA_EMBED_DIM", 4
        ):
            vec = embeddings.embed_query("hello")

        self.assertEqual(vec, [0.1, 0.2, 0.3, 0.4])
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "nomic-embed-text")

    @patch.dict(
        os.environ,
        {
            "EMBEDDING_PROVIDER_MODE": "ollama",
            "OLLAMA_EMBED_MODEL": "nomic-embed-text",
            "OLLAMA_EMBED_DIM": "768",
        },
        clear=False,
    )
    def test_signature_reports_ollama_backend(self) -> None:
        with patch.object(embeddings, "_OLLAMA_EMBED_MODEL", "nomic-embed-text"), patch.object(
            embeddings, "_OLLAMA_EMBED_DIM", 768
        ):
            sig = embeddings.embedding_backend_signature(resolve_runtime=True)
        self.assertEqual(sig["provider"], "ollama")
        self.assertEqual(sig["model"], "nomic-embed-text")
        self.assertEqual(sig["dim"], 768)


if __name__ == "__main__":
    unittest.main()
