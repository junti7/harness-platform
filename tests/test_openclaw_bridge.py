import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from scripts import openclaw_codex_bridge


class OpenClawBridgeTests(unittest.TestCase):
    @patch.object(openclaw_codex_bridge, "_probe_openclaw_gateway")
    @patch.object(openclaw_codex_bridge, "_probe_slack_bot_api")
    @patch.object(openclaw_codex_bridge, "_probe_notion_api")
    @patch.object(openclaw_codex_bridge, "run_system_integrity_check", return_value={"ok": True, "findings": []})
    @patch.object(openclaw_codex_bridge, "_can_connect_db", return_value=(True, None))
    @patch.object(openclaw_codex_bridge, "_port_open", return_value=True)
    def test_status_snapshot_uses_live_external_probes(
        self,
        _mock_port,
        _mock_db,
        _mock_integrity,
        mock_notion,
        mock_slack,
        mock_openclaw,
    ):
        mock_notion.return_value = {"available": True, "live_checked": True, "probe": "GET /v1/users/me"}
        mock_slack.return_value = {"available": True, "live_checked": True, "probe": "POST auth.test"}
        mock_openclaw.return_value = {"available": True, "live_checked": True, "probe": "openclaw health --json"}

        payload = openclaw_codex_bridge.status_snapshot()

        self.assertTrue(payload["integrations"]["notion"]["live_checked"])
        self.assertEqual(payload["integrations"]["slack_bot"]["probe"], "POST auth.test")
        self.assertEqual(payload["integrations"]["openclaw"]["probe"], "openclaw health --json")

    def test_render_ar_list_text(self):
        payload = {
            "items": [
                {"id": "AR-20260522-001", "owner": "TARS", "due_date": "2026-05-27", "summary": "스티비 연동 계획 작성", "status": "open"},
                {"id": "AR-20260522-005", "owner": "Jarvis", "due_date": "2026-05-24", "summary": "PR3 모니터링 필수 격상", "status": "open"},
            ]
        }

        rendered = openclaw_codex_bridge._render_ar_list_text(payload)

        self.assertIn("미결 AR (2건):", rendered)
        self.assertIn("AR-20260522-001", rendered)
        self.assertIn("Jarvis", rendered)
        self.assertIn("05-24", rendered)
        self.assertIn("PR3 모니터링 필수 격상", rendered)
        self.assertIn("상태", rendered)

    def test_load_ar_registry_json_fallback(self):
        with TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "ar.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-05-22T22:20:00+09:00",
                        "items": [{"id": "AR-1", "owner": "TARS", "due_date": "2026-05-27"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch.object(openclaw_codex_bridge, "AR_REGISTRY_PATH", registry_path):
                payload = openclaw_codex_bridge._load_ar_registry_json()

        self.assertEqual(payload["items"][0]["id"], "AR-1")

    def test_load_ar_tracker_jsonl_prefers_latest_by_id(self):
        with TemporaryDirectory() as tmpdir:
            tracker_path = Path(tmpdir) / "ar_tracker.jsonl"
            tracker_path.write_text(
                "\n".join(
                    [
                        json.dumps({"ar_id": "AR-1", "owner": "TARS", "due": "2026-05-27", "content": "초기", "status": "open"}, ensure_ascii=False),
                        json.dumps({"ar_id": "AR-1", "owner": "TARS", "due": "2026-05-28", "content": "갱신", "status": "open"}, ensure_ascii=False),
                        json.dumps({"ar_id": "AR-2", "owner": "KITT", "due": "2026-05-27", "content": "법무", "status": "completed"}, ensure_ascii=False),
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(openclaw_codex_bridge, "AR_TRACKER_JSONL_PATH", tracker_path):
                payload = openclaw_codex_bridge._load_ar_tracker_jsonl()

        items = {item["id"]: item for item in payload["items"]}
        self.assertEqual(items["AR-1"]["due_date"], "2026-05-28")
        self.assertEqual(items["AR-1"]["summary"], "갱신")
        self.assertEqual(items["AR-2"]["status"], "completed")

    def test_render_ar_lists_text_includes_done_when_all(self):
        payload = {
            "items": [
                {"id": "AR-1", "owner": "TARS", "due_date": "2026-05-27", "summary": "미결", "status": "open"},
                {"id": "AR-2", "owner": "KITT", "due_date": "2026-05-20", "summary": "완료", "status": "completed"},
            ]
        }

        rendered = openclaw_codex_bridge._render_ar_lists_text(payload, include_all=True)

        self.assertIn("전체 AR", rendered)
        self.assertIn("미결 AR", rendered)
        self.assertIn("완료 AR", rendered)
        self.assertIn("AR-2", rendered)

    def test_render_minutes_status_text(self):
        rows = [
            {"ts": "2026-05-23T06:00:00", "correlation_id": "orch-aaa", "ok": True, "notion_url": "https://notion.so/x"},
            {"ts": "2026-05-23T06:10:00", "correlation_id": "orch-bbb", "ok": False, "error": "boom"},
        ]

        rendered = openclaw_codex_bridge._render_minutes_status_text(rows, tail=20)

        self.assertIn("Notion 회의록 업로드 상태", rendered)
        self.assertIn("성공(ok): 1", rendered)
        self.assertIn("실패(error): 1", rendered)
        self.assertIn("orch-aaa", rendered)
        self.assertIn("orch-bbb", rendered)


if __name__ == "__main__":
    unittest.main()
