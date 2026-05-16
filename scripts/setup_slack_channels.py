import argparse
import os
import sys
import time

import httpx
from dotenv import load_dotenv


load_dotenv()

CHANNELS = [
    ("exec-president-decisions", "대표 승인, 보류, 거절, 추가 조사 요청"),
    ("vp-content-review", "부대표 콘텐츠 검토, 한국어 자연스러움, 독자 공감, paid hesitation"),
    ("ops-incidents", "실패, DLQ, budget/cost breach"),
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


def create_channel(name: str, purpose: str, is_private: bool) -> str:
    try:
        data = _slack_post(
            "conversations.create",
            {"name": name, "is_private": is_private},
        )
        channel_id = data["channel"]["id"]
    except RuntimeError as e:
        if "name_taken" not in str(e):
            raise
        channel_id = find_channel_id(name)
        if not channel_id:
            raise

    try:
        _slack_post(
            "conversations.setPurpose",
            {"channel": channel_id, "purpose": purpose[:250]},
        )
    except RuntimeError:
        pass

    return channel_id


def find_channel_id(name: str) -> str | None:
    cursor = None
    while True:
        payload = {"exclude_archived": True, "limit": 200, "types": "public_channel,private_channel"}
        if cursor:
            payload["cursor"] = cursor
        data = _slack_post("conversations.list", payload)
        for channel in data.get("channels", []):
            if channel.get("name") == name:
                return channel.get("id")
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Harness Slack operating channels.")
    parser.add_argument("--apply", action="store_true", help="Actually create channels using SLACK_BOT_TOKEN.")
    parser.add_argument("--private", action="store_true", help="Create channels as private.")
    args = parser.parse_args()

    if not args.apply:
        print("Dry run. Channels to create:")
        for name, purpose in CHANNELS:
            print(f"- #{name}: {purpose}")
        print(
            "\nRun with --apply after setting SLACK_BOT_TOKEN with Slack app scopes: "
            "incoming-webhook, chat:write, channels:read, channels:write, groups:read, groups:write."
        )
        return 0

    for name, purpose in CHANNELS:
        channel_id = create_channel(name, purpose, args.private)
        print(f"#{name} -> {channel_id}")
        time.sleep(0.3)

    return 0


if __name__ == "__main__":
    sys.exit(main())
