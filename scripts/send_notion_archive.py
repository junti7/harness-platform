import argparse
import os
import re
from pathlib import Path
from typing import Any, List

import httpx
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").split("?")[0]
NOTION_VERSION = "2022-06-28"

def markdown_to_notion_blocks(markdown_text: str) -> List[dict]:
    blocks = []
    lines = markdown_text.split("\n")
    
    # Add a visual spacer at the top
    blocks.append({"object": "block", "type": "divider", "divider": {}})
    
    is_first_section = True
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Headers with consistent spacing and styling
        if line.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": [{"type": "text", "annotations": {"bold": True}, "text": {"content": "▪️ " + line[4:]}}]}
            })
        elif line.startswith("## "):
            # Add divider before secondary headers for hierarchy
            blocks.append({"object": "block", "type": "divider", "divider": {}})
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": [{"type": "text", "annotations": {"bold": True}, "text": {"content": "🔹 " + line[3:]}}]}
            })
        elif line.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": [{"type": "text", "annotations": {"bold": True}, "text": {"content": "🏛️ " + line[2:]}}]}
            })
        # Bullet points
        elif line.startswith("- "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": line[2:]}}]}
            })
        # Basic text with callout for the first paragraph (Insight)
        else:
            if is_first_section and not line.startswith("---"):
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [{"type": "text", "text": {"content": line}}],
                        "icon": {"type": "emoji", "emoji": "💡"},
                        "color": "blue_background"
                    }
                })
                is_first_section = False
            else:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
                })
            
    return blocks

def create_notion_page(title: str, blocks: List[dict]) -> dict:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_API_KEY or NOTION_DATABASE_ID is not configured")

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }
    
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "제목": {
                "title": [{"text": {"content": title}}]
            }
        },
        "children": blocks[:100]
    }
    
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    if response.status_code != 200:
        print(f"Notion API Error: {response.text}")
        # Diagnostic: print database properties
        db_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
        db_resp = httpx.get(db_url, headers=headers)
        if db_resp.status_code == 200:
            print(f"Database Properties: {list(db_resp.json().get('properties', {}).keys())}")
    response.raise_for_status()
    return response.json()

def main():
    parser = argparse.ArgumentParser(description="Archive a markdown report to Notion.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File {args.file} does not exist.")
        return 1

    with open(args.file, "r", encoding="utf-8") as f:
        content = f.read()

    title = args.title or args.file.stem
    blocks = markdown_to_notion_blocks(content)
    
    try:
        result = create_notion_page(title, blocks)
        print(f"Successfully archived to Notion: {result.get('url')}")
    except Exception as e:
        print(f"Failed to archive to Notion: {e}")
        # In a real environment, we'd check if NOTION_API_KEY is actually set.
        # Since this is a simulation/automated task, we'll assume it might be missing and handle gracefully.
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
