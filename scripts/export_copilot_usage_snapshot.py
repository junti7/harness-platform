#!/usr/bin/env python3
"""Export a prompt-free Copilot CLI usage summary and optionally sync it."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import tempfile
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_snapshot(state_dir: Path, day: str) -> dict:
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=KST)
    end = start + timedelta(days=1)
    models: Counter[str] = Counter()
    sessions: set[str] = set()
    turns = 0
    completed_turns = 0
    auto_resolutions = 0

    for path in state_dir.glob("*/events.jsonl"):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                event = json.loads(line)
                timestamp = _parse_time(str(event["timestamp"])).astimezone(KST)
            except (KeyError, ValueError, TypeError, json.JSONDecodeError):
                continue
            if not start <= timestamp < end:
                continue
            event_type = event.get("type")
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            if event_type == "session.start":
                sessions.add(str(data.get("sessionId") or path.parent.name))
            elif event_type == "session.auto_mode_resolved":
                model = str(data.get("chosenModel") or "unknown")
                models[model] += 1
                auto_resolutions += 1
            elif event_type == "assistant.turn_start":
                turns += 1
            elif event_type == "assistant.turn_end":
                completed_turns += 1

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    snapshot = {
        "schema": "harness.copilot_usage_snapshot.v1",
        "generated_at": generated_at,
        "day": day,
        "timezone": "Asia/Seoul",
        "source": "copilot_cli_local_session_events",
        "privacy": "aggregate_only_no_prompts_no_responses",
        "sessions": len(sessions),
        "turns_started": turns,
        "turns_completed": completed_turns,
        "auto_model_resolutions": auto_resolutions,
        "models": dict(sorted(models.items())),
    }
    canonical = json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical).hexdigest()
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--day",
        default=(datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path.home() / ".copilot" / "session-state",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sync-target")
    args = parser.parse_args()

    snapshot = build_snapshot(args.state_dir, args.day)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=args.output.parent, delete=False
    ) as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, args.output)

    if args.sync_target:
        completed = subprocess.run(
            [
                "/usr/bin/rsync",
                "-az",
                "--delay-updates",
                str(args.output),
                args.sync_target,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode != 0:
            raise SystemExit(completed.stderr.strip() or "rsync failed")
    print(json.dumps(snapshot, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
