"""Save orchestration meeting minutes to Notion.

Requires env:
  NOTION_API_KEY
  NOTION_MINUTES_DATABASE_ID  (별도 회의록 DB; 없으면 NOTION_DATABASE_ID 사용)

Database must have a title property named "제목".
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_MINUTES_DATABASE_ID = (
    os.getenv("NOTION_MINUTES_DATABASE_ID")
    or os.getenv("NOTION_DATABASE_ID", "")
).split("?")[0]
NOTION_VERSION = "2022-06-28"


def _rich(text: str, bold: bool = False, color: str | None = None) -> dict:
    ann: dict[str, Any] = {"bold": bold}
    node: dict[str, Any] = {"type": "text", "text": {"content": text[:2000]}, "annotations": ann}
    return node


def _blocks_from_markdown(md: str) -> list[dict]:
    blocks: list[dict] = []
    for line in md.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                            "heading_3": {"rich_text": [_rich(s[4:], bold=True)]}})
        elif s.startswith("## "):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            blocks.append({"object": "block", "type": "heading_2",
                            "heading_2": {"rich_text": [_rich("🔹 " + s[3:], bold=True)]}})
        elif s.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                            "heading_1": {"rich_text": [_rich("🏛️ " + s[2:], bold=True)]}})
        elif s.startswith("- ") or s.startswith("* "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                            "bulleted_list_item": {"rich_text": [_rich(s[2:])]}})
        elif re.match(r"^\d+\. ", s):
            content = re.sub(r"^\d+\. ", "", s)
            blocks.append({"object": "block", "type": "numbered_list_item",
                            "numbered_list_item": {"rich_text": [_rich(content)]}})
        elif s.startswith("|") and s.endswith("|"):
            # 테이블 행 → bullet로 변환 (Notion API 테이블은 구현 복잡)
            cells = [c.strip() for c in s.strip("|").split("|") if c.strip() and c.strip() != "---"]
            if cells:
                blocks.append({"object": "block", "type": "bulleted_list_item",
                                "bulleted_list_item": {"rich_text": [_rich(" | ".join(cells))]}})
        elif s.startswith("---"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                            "paragraph": {"rich_text": [_rich(s)]}})
    return blocks


def save_minutes(
    correlation_id: str,
    order: str,
    personas: list[str],
    minutes_text: str,
    cost_usd: float,
) -> str | None:
    """Create a Notion page with meeting minutes. Returns page URL or None on failure."""
    if not NOTION_API_KEY or not NOTION_MINUTES_DATABASE_ID:
        return None

    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"[회의록] {date_str} — {correlation_id}"

    meta_blocks: list[dict] = [
        {"object": "block", "type": "callout", "callout": {
            "rich_text": [_rich(f"📋 {order[:200]}")],
            "icon": {"type": "emoji", "emoji": "📋"},
            "color": "blue_background",
        }},
        {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [_rich(f"참여 팀: {', '.join(personas)}  |  비용: ${cost_usd:.3f}  |  ID: {correlation_id}")]}},
        {"object": "block", "type": "divider", "divider": {}},
    ]
    content_blocks = _blocks_from_markdown(minutes_text)
    all_blocks = (meta_blocks + content_blocks)[:100]

    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    payload = {
        "parent": {"database_id": NOTION_MINUTES_DATABASE_ID},
        "properties": {"제목": {"title": [{"text": {"content": title}}]}},
        "children": all_blocks,
    }
    try:
        r = httpx.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=30.0)
        r.raise_for_status()
        return r.json().get("url")
    except Exception as exc:
        print(f"[notion_minutes] 저장 실패: {exc}")
        return None
