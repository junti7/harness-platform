#!/usr/bin/env python3
"""Create one user-requested Harness Notion archive entry from JSON stdin."""

from __future__ import annotations

import hashlib
import json
import sys

from scripts.notion_archive_entry import create_archive_page


def main() -> int:
    payload = json.load(sys.stdin)
    title = str(payload.get("title") or "").strip()
    body = str(payload.get("body") or "").strip()
    if not title or not body:
        raise ValueError("title and body are required")
    if len(title) > 200 or len(body) > 20_000:
        raise ValueError("Notion archive input exceeds the bounded size")
    content_hash = hashlib.sha256((title + "\n" + body).encode()).hexdigest()[:16]

    page = create_archive_page(
        title=title,
        body_markdown=body,
        artifact_type=str(payload.get("artifactType") or "ops_brief"),
        teams=[str(item) for item in (payload.get("teams") or ["Chief of Staff"])][:5],
        project=str(payload.get("project") or "Harness Platform"),
        source_channel=str(payload.get("sourceChannel") or "Discord"),
        event_date=str(payload.get("eventDate") or "") or None,
        reminder_date=str(payload.get("reminderDate") or "") or None,
        canonical_key=str(payload.get("canonicalKey") or "").strip()
        or f"openclaw-notion-{content_hash}",
        summary=str(payload.get("summary") or body[:1_900]),
        decision_summary=str(payload.get("decisionSummary") or "") or None,
        action_items=str(payload.get("actionItems") or "") or None,
        historical_value=str(payload.get("historicalValue") or "high"),
        confidentiality="internal",
        tags=[str(item) for item in (payload.get("tags") or [])][:10],
        strict=True,
    )
    print(json.dumps({"ok": True, "page_id": page.get("id"), "url": page.get("url")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
