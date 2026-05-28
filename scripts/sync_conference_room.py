#!/usr/bin/env python3
"""Slack #회의실 채널 → conference_room_stream.jsonl 동기화."""
import json, os, sys
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    sys.exit("pip install requests")

PROJECT_ROOT = Path(__file__).parent.parent
OUT_PATH = PROJECT_ROOT / "docs" / "reports" / "conference_room_stream.jsonl"

TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
CHANNEL = os.environ.get("SLACK_CHANNEL_CONFERENCE_ROOM", "").strip()


def ts_to_iso(ts: str) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def slack_get(method: str, params: dict) -> dict:
    r = requests.get(
        f"https://slack.com/api/{method}",
        headers={"Authorization": f"Bearer {TOKEN}"},
        params=params,
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        print(f"  Slack warning [{method}]: {data.get('error')}", file=sys.stderr)
    return data


def fetch_history(limit: int = 200) -> list[dict]:
    data = slack_get("conversations.history", {"channel": CHANNEL, "limit": limit})
    return data.get("messages", [])


def fetch_replies(thread_ts: str) -> list[dict]:
    data = slack_get("conversations.replies", {"channel": CHANNEL, "ts": thread_ts})
    return data.get("messages", []) if data.get("ok") else []


def user_display(msg: dict) -> str:
    return msg.get("username") or msg.get("user") or "unknown"


def main():
    if not TOKEN or not CHANNEL:
        sys.exit("SLACK_BOT_TOKEN 또는 SLACK_CHANNEL_CONFERENCE_ROOM 미설정")

    messages = fetch_history(200)
    print(f"채널에서 {len(messages)}개 메시지 수신")

    rows: list[dict] = []
    seen_threads: set[str] = set()

    for root_msg in messages:
        thread_ts = root_msg.get("thread_ts") or root_msg["ts"]
        if thread_ts in seen_threads:
            continue
        seen_threads.add(thread_ts)

        reply_count = int(root_msg.get("reply_count") or 0)
        all_msgs = fetch_replies(thread_ts) if reply_count > 0 else [root_msg]

        for msg in all_msgs:
            rows.append({
                "id": msg["ts"],
                "thread_id": thread_ts,
                "posted_at": ts_to_iso(msg["ts"]),
                "author_display": user_display(msg),
                "author_role": None,
                "text_markdown": msg.get("text", ""),
                "is_reply": msg["ts"] != thread_ts,
                "title": root_msg.get("text", "")[:80] if msg["ts"] == thread_ts else None,
                "correlation_id": None,
                "title_pending": False,
                "agenda_pending": False,
            })

    rows.sort(key=lambda r: r["posted_at"])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"✅ {len(rows)}개 메시지 → {OUT_PATH}")


if __name__ == "__main__":
    main()
