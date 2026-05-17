import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").split("?")[0]
NOTION_VERSION = "2022-06-28"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def main() -> int:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_API_KEY or NOTION_DATABASE_ID missing")

    db_resp = httpx.get(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
        headers=_headers(),
        timeout=20.0,
    )
    db_resp.raise_for_status()
    db = db_resp.json()

    query_resp = httpx.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=_headers(),
        json={"page_size": 5},
        timeout=20.0,
    )
    query_resp.raise_for_status()
    sample = query_resp.json()

    payload = {
        "database_id": db.get("id"),
        "title": db.get("title"),
        "url": db.get("url"),
        "properties": {
            name: {"type": spec.get("type")}
            for name, spec in (db.get("properties") or {}).items()
        },
        "sample_count": len(sample.get("results") or []),
        "sample_titles": [],
    }

    for page in sample.get("results") or []:
        title = None
        for prop in (page.get("properties") or {}).values():
            if prop.get("type") == "title":
                title_items = prop.get("title") or []
                if title_items:
                    title = "".join(item.get("plain_text", "") for item in title_items)
                    break
        payload["sample_titles"].append(title or "(untitled)")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
