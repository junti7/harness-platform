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


def _bounded_counts(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.most_common(100)))


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_snapshot(state_dir: Path, day: str) -> dict:
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=KST)
    end = start + timedelta(days=1)
    models: Counter[str] = Counter()
    sessions: set[str] = set()
    active_sessions: set[str] = set()
    turns = 0
    completed_turns = 0
    auto_resolutions = 0
    producers: Counter[str] = Counter()
    repositories: Counter[str] = Counter()
    repository_hosts: Counter[str] = Counter()
    copilot_versions: Counter[str] = Counter()

    for path in state_dir.glob("*/events.jsonl"):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        events = []
        for line in lines:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
        session_start = next(
            (event for event in events if event.get("type") == "session.start"),
            {},
        )
        start_data = (
            session_start.get("data")
            if isinstance(session_start.get("data"), dict)
            else {}
        )
        context = (
            start_data.get("context")
            if isinstance(start_data.get("context"), dict)
            else {}
        )
        session_had_usage = False
        for event in events:
            try:
                timestamp = _parse_time(str(event["timestamp"])).astimezone(KST)
            except (KeyError, ValueError, TypeError):
                continue
            if not start <= timestamp < end:
                continue
            event_type = event.get("type")
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            if event_type == "session.start":
                sessions.add(str(data.get("sessionId") or path.parent.name))
                session_had_usage = True
            elif event_type == "session.auto_mode_resolved":
                model = str(data.get("chosenModel") or "unknown")
                models[model] += 1
                auto_resolutions += 1
                session_had_usage = True
            elif event_type == "assistant.turn_start":
                turns += 1
                session_had_usage = True
            elif event_type == "assistant.turn_end":
                completed_turns += 1
                session_had_usage = True
        if session_had_usage:
            active_sessions.add(str(start_data.get("sessionId") or path.parent.name))
            producers[str(start_data.get("producer") or "unknown")] += 1
            repositories[str(context.get("repository") or "unknown")] += 1
            repository_hosts[str(context.get("repositoryHost") or "unknown")] += 1
            copilot_versions[str(start_data.get("copilotVersion") or "unknown")] += 1

    known_producers = [key for key in producers if key != "unknown"]
    known_repositories = [key for key in repositories if key != "unknown"]
    known_hosts = [key for key in repository_hosts if key != "unknown"]
    fully_attributed = (
        len(known_producers) == len(known_repositories) == len(known_hosts) == 1
        and "unknown" not in producers
        and "unknown" not in repositories
        and "unknown" not in repository_hosts
        and max(
            len(producers),
            len(repositories),
            len(repository_hosts),
            len(copilot_versions),
        )
        <= 100
        and sum(producers.values()) == len(active_sessions)
        and sum(repositories.values()) == len(active_sessions)
        and sum(repository_hosts.values()) == len(active_sessions)
    )
    producer = (
        known_producers[0]
        if len(known_producers) == 1
        else "mixed" if len(known_producers) > 1 else "unknown"
    )
    observed_origin = {
        "client": "GitHub Copilot CLI"
        if producer == "copilot-agent"
        else "mixed" if producer == "mixed" else "unknown",
        "producer": producer,
        "repository": known_repositories[0]
        if len(known_repositories) == 1
        else "mixed" if len(known_repositories) > 1 else "unknown",
        "repository_host": known_hosts[0]
        if len(known_hosts) == 1
        else "mixed" if len(known_hosts) > 1 else "unknown",
        "confidence": "high" if fully_attributed else "partial",
    }

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    snapshot = {
        "schema": "harness.copilot_usage_snapshot.v1",
        "generated_at": generated_at,
        "day": day,
        "timezone": "Asia/Seoul",
        "source": "copilot_cli_local_session_events",
        "privacy": "aggregate_attribution_no_prompts_no_responses_no_paths",
        "sessions": len(sessions),
        "sessions_with_activity": len(active_sessions),
        "turns_started": turns,
        "turns_completed": completed_turns,
        "auto_model_resolutions": auto_resolutions,
        "models": dict(sorted(models.items())),
        "observed_origin": observed_origin,
        "attribution_basis": "session_start_metadata_for_in_window_usage",
        "attribution_scope": "locally_recorded_copilot_cli_sessions_only",
        "attribution_breakdown_truncated": max(
            len(producers),
            len(repositories),
            len(repository_hosts),
            len(copilot_versions),
        )
        > 100,
        "session_attribution": {
            "producers": _bounded_counts(producers),
            "repositories": _bounded_counts(repositories),
            "repository_hosts": _bounded_counts(repository_hosts),
            "copilot_versions": _bounded_counts(copilot_versions),
        },
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
