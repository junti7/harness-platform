"""Notion reminder check — daily job.

Queries the archive DB for pages where Reminder Date <= today,
then sends a Slack digest. Also flags pages where Last Reviewed
is older than STALE_DAYS and Historical Value = high.

Usage:
    python3 scripts/notion_reminder_check.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").split("?")[0]
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
NOTION_VERSION = "2022-06-28"
STALE_DAYS = 30  # high-value records not reviewed in this many days are flagged


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _query_due_reminders(today: str) -> list[dict[str, Any]]:
    """Pages where Reminder Date exists and <= today."""
    payload = {
        "filter": {
            "and": [
                {"property": "Reminder Date", "date": {"on_or_before": today}},
            ]
        },
        "sorts": [{"property": "Reminder Date", "direction": "ascending"}],
        "page_size": 50,
    }
    resp = httpx.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=_headers(),
        json=payload,
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _query_stale_high_value(stale_cutoff: str) -> list[dict[str, Any]]:
    """High-value pages not reviewed since stale_cutoff."""
    payload = {
        "filter": {
            "and": [
                {"property": "Historical Value", "select": {"equals": "high"}},
                {
                    "or": [
                        {"property": "Last Reviewed", "date": {"on_or_before": stale_cutoff}},
                        {"property": "Last Reviewed", "date": {"is_empty": True}},
                    ]
                },
            ]
        },
        "sorts": [{"property": "Last Reviewed", "direction": "ascending"}],
        "page_size": 20,
    }
    resp = httpx.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=_headers(),
        json=payload,
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def _page_title(page: dict) -> str:
    try:
        return page["properties"]["제목"]["title"][0]["text"]["content"]
    except (KeyError, IndexError):
        return page.get("id", "untitled")[:8]


def _page_url(page: dict) -> str:
    return page.get("url", "")


def _prop_text(page: dict, key: str) -> str:
    try:
        prop = page["properties"][key]
        ptype = prop.get("type", "")
        if ptype == "date":
            d = prop.get("date") or {}
            return d.get("start", "")
        if ptype == "rich_text":
            items = prop.get("rich_text", [])
            return items[0]["text"]["content"] if items else ""
        if ptype == "select":
            s = prop.get("select") or {}
            return s.get("name", "")
    except (KeyError, IndexError):
        pass
    return ""


def _update_last_reviewed(page_id: str, today: str) -> None:
    httpx.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={"properties": {"Last Reviewed": {"date": {"start": today}}}},
        timeout=10.0,
    ).raise_for_status()


def _send_slack(text: str) -> None:
    if not SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL == "your_webhook_here":
        print("[Slack skip] webhook not configured")
        return
    httpx.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10.0).raise_for_status()


def run(dry_run: bool = False) -> dict[str, int]:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_API_KEY or NOTION_DATABASE_ID missing")

    today = str(date.today())
    stale_cutoff = str(date.today() - timedelta(days=STALE_DAYS))

    due = _query_due_reminders(today)
    stale = _query_stale_high_value(stale_cutoff)

    # deduplicate stale against due
    due_ids = {p["id"] for p in due}
    stale = [p for p in stale if p["id"] not in due_ids]

    if not due and not stale:
        print(f"[{today}] 리마인더 없음, stale 없음")
        return {"due": 0, "stale": 0}

    lines = [f"*[Harness Notion Reminder]* {today}"]

    if due:
        lines.append(f"\n📅 *리마인더 도래* ({len(due)}건)")
        for p in due:
            title = _page_title(p)
            reminder = _prop_text(p, "Reminder Date")
            summary = _prop_text(p, "Summary")
            url = _page_url(p)
            lines.append(f"• <{url}|{title}> — Reminder: {reminder}")
            if summary:
                lines.append(f"  _{summary[:120]}_")

    if stale:
        lines.append(f"\n🔄 *High-value stale* (Last Reviewed > {STALE_DAYS}일, {len(stale)}건)")
        for p in stale:
            title = _page_title(p)
            last = _prop_text(p, "Last Reviewed") or "없음"
            url = _page_url(p)
            lines.append(f"• <{url}|{title}> — Last Reviewed: {last}")

    message = "\n".join(lines)
    print(message)

    if not dry_run:
        _send_slack(message)
        # mark due items as reviewed today
        for p in due:
            try:
                _update_last_reviewed(p["id"], today)
            except Exception as e:
                print(f"  [warn] Last Reviewed 업데이트 실패 {p['id']}: {e}")

    return {"due": len(due), "stale": len(stale)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Notion reminder & stale record check")
    parser.add_argument("--dry-run", action="store_true", help="Slack 발송 없이 출력만")
    args = parser.parse_args()
    result = run(dry_run=args.dry_run)
    print(f"\n완료: due={result['due']}, stale={result['stale']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
