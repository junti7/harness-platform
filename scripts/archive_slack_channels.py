import argparse
import os
import sys
import time

import httpx
from dotenv import load_dotenv


load_dotenv()

KEEP_CHANNELS = {
    "exec-president-decisions",
    "vp-content-review",
    "ops-incidents",
}

HARNESS_CHANNELS = [
    "exec-president-decisions",
    "exec-capital-actions",
    "exec-daily-brief",
    "vp-content-review",
    "vp-customer-narratives",
    "vp-relationship-map",
    "hr-vp-ojt",
    "hr-vp-assessments",
    "hr-president-reports",
    "intel-evidence-feed",
    "intel-signals",
    "intel-opportunities",
    "intel-research-reviews",
    "revenue-experiments",
    "customer-validation",
    "product-reports",
    "eng-codex",
    "agent-github-copilot",
    "agent-claude-strategy",
    "agent-gemini-research",
    "agent-gpt-evaluation",
    "agent-local-gate",
    "agent-openclaw-routing",
    "ops-agent-runs",
    "ops-incidents",
    "security-permissions",
]


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
        details = []
        for key in ("needed", "provided"):
            if data.get(key):
                details.append(f"{key}={data[key]}")
        suffix = f" ({', '.join(details)})" if details else ""
        raise RuntimeError(f"Slack API error at {endpoint}: {data.get('error')}{suffix}")
    return data


def list_channels(include_archived: bool = False) -> dict[str, str]:
    channels = {}
    cursor = None
    while True:
        payload = {
            "exclude_archived": not include_archived,
            "limit": 200,
            "types": "public_channel,private_channel",
        }
        if cursor:
            payload["cursor"] = cursor
        data = _slack_post("conversations.list", payload)
        for channel in data.get("channels", []):
            if not include_archived and channel.get("is_archived"):
                continue
            channels[channel["name"]] = channel["id"]
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return channels


def archive_channel(channel_id: str) -> None:
    _slack_post("conversations.archive", {"channel": channel_id})


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive non-Phase-1 Harness Slack channels.")
    parser.add_argument("--apply", action="store_true", help="Archive channels. Without this, only print the plan.")
    args = parser.parse_args()

    channels_by_name = list_channels()
    targets = [
        name
        for name in HARNESS_CHANNELS
        if name not in KEEP_CHANNELS and name in channels_by_name
    ]

    print("Keep:")
    for name in sorted(KEEP_CHANNELS):
        print(f"- #{name}")

    print("\nArchive:")
    for name in targets:
        print(f"- #{name} -> {channels_by_name[name]}")

    missing = [
        name
        for name in HARNESS_CHANNELS
        if name not in KEEP_CHANNELS and name not in channels_by_name
    ]
    if missing:
        print("\nAlready missing or archived:")
        for name in missing:
            print(f"- #{name}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to archive these channels.")
        return 0

    for name in targets:
        archive_channel(channels_by_name[name])
        print(f"Archived #{name}")
        time.sleep(0.3)

    return 0


if __name__ == "__main__":
    sys.exit(main())
