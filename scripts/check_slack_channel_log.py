"""Reconcile live Slack channels against SLACK_CHANNEL_CREATION_LOG.md.

Charter §6 / CLAUDE.md Must rule: every persona-created Slack channel must have a
log entry recorded BEFORE creation. This script is the technical gate that keeps
that rule from being honor-system: it lists channels that exist in Slack but have
no corresponding log entry, and (optionally) alerts #ops-incidents.

Usage:
    python scripts/check_slack_channel_log.py            # dry run, print report
    python scripts/check_slack_channel_log.py --alert    # also post violations to #ops-incidents
    python scripts/check_slack_channel_log.py --json      # machine-readable output
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = PROJECT_ROOT / "docs/operations/SLACK_CHANNEL_CREATION_LOG.md"

# Channels that predate the log requirement (Phase 1 baseline, SLACK_OPERATING_SYSTEM.md).
# Includes pre-orchestration workspace channels snapshotted at 2026-05-20 (Charter §6 start).
GRANDFATHERED = {
    "exec-president-decisions",
    "vp-content-review",
    "ops-incidents",
    # Pre-orchestration workspace defaults (snapshot 2026-05-20):
    "slack-전체",
    "새-채널",
    "소셜",
}

# Example/placeholder names in the log that must never count as real entries.
LOG_PLACEHOLDERS = {"example-do-not-create"}


def _headers() -> dict:
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _slack_post(endpoint: str, payload: dict) -> dict:
    response = httpx.post(
        f"https://slack.com/api/{endpoint}",
        headers=_headers(),
        json=payload,
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack API error at {endpoint}: {data.get('error')}")
    return data


def list_live_channels() -> dict[str, str]:
    channels: dict[str, str] = {}
    cursor = None
    while True:
        payload = {
            "exclude_archived": True,
            "limit": 200,
            "types": "public_channel,private_channel",
        }
        if cursor:
            payload["cursor"] = cursor
        data = _slack_post("conversations.list", payload)
        for channel in data.get("channels", []):
            if channel.get("is_archived"):
                continue
            channels[channel["name"]] = channel["id"]
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return channels


def parse_logged_channels(log_path: Path = LOG_PATH) -> set[str]:
    """Extract channel names from the markdown table's channel_name column.

    Channel names are recorded as `#name` (backtick-wrapped). We collect every
    backtick-wrapped #token in table rows, then drop known placeholders.
    """
    if not log_path.exists():
        raise RuntimeError(f"Channel creation log not found: {log_path}")

    names: set[str] = set()
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        for match in re.findall(r"`#([A-Za-z0-9_\-가-힣]+)`", line):
            names.add(match)
    return names - LOG_PLACEHOLDERS


def find_violations() -> list[str]:
    live = list_live_channels()
    logged = parse_logged_channels()
    return sorted(
        name
        for name in live
        if name not in logged and name not in GRANDFATHERED
    )


def alert_ops_incidents(violations: list[str]) -> None:
    channel_id = os.getenv("SLACK_CHANNEL_OPS_INCIDENTS", "")
    if not channel_id:
        raise RuntimeError("SLACK_CHANNEL_OPS_INCIDENTS is not configured")
    listing = "\n".join(f"- #{name}" for name in violations)
    text = (
        ":rotating_light: *Channel creation log violation*\n"
        f"로그 entry 없이 존재하는 Slack 채널 {len(violations)}개 (Charter §6):\n"
        f"{listing}\n"
        "해당 채널 생성 persona를 추적하고 SLACK_CHANNEL_CREATION_LOG.md에 보강하세요."
    )
    _slack_post("chat.postMessage", {"channel": channel_id, "text": text})


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile Slack channels against the creation log.")
    parser.add_argument("--alert", action="store_true", help="Post violations to #ops-incidents.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    violations = find_violations()

    if args.json:
        print(json.dumps({"violations": violations, "count": len(violations)}, ensure_ascii=False))
    else:
        if violations:
            print(f"Unlogged channels ({len(violations)}):")
            for name in violations:
                print(f"- #{name}")
            print("\nCharter §6 위반: 로그 없는 채널. SLACK_CHANNEL_CREATION_LOG.md에 보강 필요.")
        else:
            print("OK: 모든 활성 채널이 로그에 기록되어 있습니다 (또는 grandfathered).")

    if args.alert and violations:
        alert_ops_incidents(violations)
        print(f"\nAlerted #ops-incidents about {len(violations)} violation(s).")

    # Non-zero exit when violations exist, so launchd/cron can detect failure.
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
