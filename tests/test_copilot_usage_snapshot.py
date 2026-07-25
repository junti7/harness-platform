import json
from pathlib import Path

from scripts.export_copilot_usage_snapshot import build_snapshot


def test_build_snapshot_aggregates_without_content(tmp_path: Path) -> None:
    session = tmp_path / "session-1"
    session.mkdir()
    events = [
        {
            "type": "session.start",
            "timestamp": "2026-07-23T16:00:00Z",
            "data": {"sessionId": "session-1"},
        },
        {
            "type": "session.auto_mode_resolved",
            "timestamp": "2026-07-23T16:00:01Z",
            "data": {"chosenModel": "gpt-5.3-codex"},
        },
        {
            "type": "user.message",
            "timestamp": "2026-07-23T16:00:02Z",
            "data": {"content": "secret prompt"},
        },
        {
            "type": "assistant.turn_start",
            "timestamp": "2026-07-23T16:00:03Z",
            "data": {"model": "gpt-5.3-codex"},
        },
    ]
    (session / "events.jsonl").write_text(
        "\n".join(json.dumps(row) for row in events), encoding="utf-8"
    )

    snapshot = build_snapshot(tmp_path, "2026-07-24")

    assert snapshot["sessions"] == 1
    assert snapshot["models"] == {"gpt-5.3-codex": 1}
    assert snapshot["turns_started"] == 1
    assert len(snapshot["snapshot_sha256"]) == 64
    assert "secret prompt" not in json.dumps(snapshot)
