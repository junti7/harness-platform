import unittest


class TestIbkrEtfBridgeRendering(unittest.TestCase):
    def test_render_preflight_fail(self) -> None:
        from scripts.openclaw_codex_bridge import _render_ibkr_etf_check_text

        payload = {
            "whitelist_path": "docs/trading/etf_whitelist_v0.json",
            "preflight": {
                "ok": False,
                "error": "Connection refused",
                "base_url": "https://localhost:5000/v1/api",
                "tls_verify": False,
            },
            "results": [],
        }
        text = _render_ibkr_etf_check_text(payload)
        self.assertIn("IBKR", text)
        self.assertIn("연결 실패", text)
        self.assertIn("Connection refused", text)

    def test_render_ok_includes_next_step(self) -> None:
        from scripts.openclaw_codex_bridge import _render_ibkr_etf_check_text

        payload = {
            "whitelist_path": "docs/trading/etf_whitelist_v0.json",
            "preflight": {"ok": True, "auth": {"authenticated": True}},
            "results": [
                {
                    "item": {"id": "us-SMH", "query": "SMH"},
                    "candidate_count": 3,
                    "best": {"conid": "123", "confidence": 0.9},
                }
            ],
        }
        text = _render_ibkr_etf_check_text(payload)
        self.assertIn("read-only", text)
        self.assertIn("ibkr etf approve", text.lower())

    def test_render_auth_false_blocks(self) -> None:
        from scripts.openclaw_codex_bridge import _render_ibkr_etf_check_text

        payload = {
            "whitelist_path": "docs/trading/etf_whitelist_v0.json",
            "preflight": {"ok": True, "auth": {"authenticated": False}},
            "results": [],
        }
        text = _render_ibkr_etf_check_text(payload)
        self.assertIn("authenticated", text)
        self.assertIn("중단", text)


if __name__ == "__main__":
    unittest.main()
