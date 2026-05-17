"""Weekly goal snapshot reminder.

Sends a Slack message with manual snapshot instructions.
Intended to run weekly (every Sunday) via launchd.

Usage:
    python scripts/goal_weekly_reminder.py [--goal-id GOAL_ID]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.goal_loop import get_goal_status


def _send_slack(text: str) -> bool:
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook:
        print("[WARN] SLACK_WEBHOOK_URL not set — printing to stdout only.")
        print(text)
        return False
    import urllib.request
    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(webhook, data=payload,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[ERROR] Slack send failed: {e}")
        return False


def _build_reminder(goal_id: int) -> str:
    try:
        status = get_goal_status(goal_id)
    except Exception as e:
        return f"[goal_weekly_reminder] goal_id={goal_id} 조회 실패: {e}"

    title = status.get("title", f"Goal #{goal_id}")
    target_value = status.get("target_value", "?")
    current_value = status.get("current_value", "?")
    deadline = str(status.get("deadline", ""))[:10]
    health = status.get("health_status", "?")
    metric = status.get("target_metric", "?")
    today = date.today().isoformat()
    week_num = datetime.now().isocalendar()[1]

    health_emoji = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(health, "⚪")

    lines = [
        f"📊 *주간 Goal 스냅샷 리마인더* — Week {week_num} ({today})",
        "",
        f"*{title}*",
        f"{health_emoji} 현재: {current_value} / 목표: {target_value} {metric} (기한: {deadline})",
        "",
        "🔢 이번 주 실제 구독자 수를 확인하고 아래 명령어로 기록해 주세요:",
        "```",
        f"python scripts/openclaw_codex_bridge.py goal-snapshot {goal_id} \\",
        f"  --actual-value <실제_구독자_수> \\",
        f"  --health-status <green|yellow|red> \\",
        f"  --notes 'Week {week_num} manual snapshot'",
        "```",
        "",
        "구독자 확인: https://substack.com/home (대시보드 → Subscribers)",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send weekly goal snapshot reminder to Slack")
    parser.add_argument("--goal-id", type=int, default=1, help="Goal ID to remind about (default: 1)")
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    message = _build_reminder(args.goal_id)
    sent = _send_slack(message)
    if sent:
        print(f"[OK] Slack reminder sent for goal #{args.goal_id}")
    else:
        print(f"[DONE] Reminder printed (Slack not configured or failed)")


if __name__ == "__main__":
    main()
