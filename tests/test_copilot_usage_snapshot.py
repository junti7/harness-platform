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
            "data": {
                "sessionId": "session-1",
                "producer": "copilot-agent",
                "copilotVersion": "1.0.74",
                "context": {
                    "repository": "junti7/harness-platform",
                    "repositoryHost": "github.com",
                    "cwd": "/private/secret/path",
                },
            },
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
    assert snapshot["sessions_with_activity"] == 1
    assert snapshot["models"] == {"gpt-5.3-codex": 1}
    assert snapshot["turns_started"] == 1
    assert snapshot["observed_origin"] == {
        "client": "GitHub Copilot CLI",
        "producer": "copilot-agent",
        "repository": "junti7/harness-platform",
        "repository_host": "github.com",
        "confidence": "high",
    }
    assert snapshot["session_attribution"]["producers"] == {"copilot-agent": 1}
    assert snapshot["attribution_scope"] == "locally_recorded_copilot_cli_sessions_only"
    assert snapshot["attribution_breakdown_truncated"] is False
    assert snapshot["session_attribution"]["repositories"] == {
        "junti7/harness-platform": 1
    }
    assert len(snapshot["snapshot_sha256"]) == 64
    assert "secret prompt" not in json.dumps(snapshot)
    assert "/private/secret/path" not in json.dumps(snapshot)


def test_build_snapshot_marks_mixed_known_and_unknown_origin_partial(
    tmp_path: Path,
) -> None:
    for name, producer, repository, host in (
        ("known", "copilot-agent", "junti7/harness-platform", "github.com"),
        ("unknown", None, None, None),
    ):
        session = tmp_path / name
        session.mkdir()
        rows = [
            {
                "type": "session.start",
                "timestamp": "2026-07-23T16:00:00Z",
                "data": {
                    "sessionId": name,
                    "producer": producer,
                    "context": {
                        "repository": repository,
                        "repositoryHost": host,
                    },
                },
            },
            {"malformed": "row"},
            {
                "type": "assistant.turn_start",
                "timestamp": "2026-07-23T16:00:01Z",
                "data": {},
            },
        ]
        (session / "events.jsonl").write_text(
            "\n".join(json.dumps(row) for row in rows) + "\nnot-json",
            encoding="utf-8",
        )

    snapshot = build_snapshot(tmp_path, "2026-07-24")

    assert snapshot["sessions"] == 2
    assert snapshot["sessions_with_activity"] == 2
    assert snapshot["observed_origin"]["producer"] == "copilot-agent"
    assert snapshot["observed_origin"]["confidence"] == "partial"
    assert snapshot["session_attribution"]["producers"] == {
        "copilot-agent": 1,
        "unknown": 1,
    }
