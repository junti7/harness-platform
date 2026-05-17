import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").split("?")[0]
NOTION_VERSION = "2022-06-28"

ARCHIVE_PROPERTIES = {
    "Artifact Type": {
        "select": {
            "options": [
                {"name": "project"},
                {"name": "goal"},
                {"name": "meeting_note"},
                {"name": "strategy_memo"},
                {"name": "decision_card"},
                {"name": "experiment"},
                {"name": "success_case"},
                {"name": "failure_case"},
                {"name": "issue_archive"},
                {"name": "research_report"},
                {"name": "sop"},
                {"name": "ops_brief"},
            ]
        }
    },
    "Team": {
        "multi_select": {
            "options": [
                {"name": "Chief of Staff"},
                {"name": "Business Operations"},
                {"name": "Marketing Strategy"},
                {"name": "Subscriber Growth"},
                {"name": "Sales"},
                {"name": "Product Planning"},
                {"name": "Vice President Review"},
                {"name": "Red Team"},
                {"name": "Legal Counsel"},
                {"name": "QA"},
                {"name": "Engineering"},
            ]
        }
    },
    "Project": {"rich_text": {}},
    "Goal ID": {"number": {"format": "number"}},
    "Goal Metric": {"rich_text": {}},
    "Project Status": {
        "select": {
            "options": [
                {"name": "draft"},
                {"name": "planning"},
                {"name": "active"},
                {"name": "review"},
                {"name": "blocked"},
                {"name": "done"},
                {"name": "archived"},
            ]
        }
    },
    "Outcome": {
        "select": {
            "options": [
                {"name": "success"},
                {"name": "failure"},
                {"name": "mixed"},
                {"name": "pending"},
                {"name": "n/a"},
            ]
        }
    },
    "Source Channel": {
        "select": {
            "options": [
                {"name": "slack"},
                {"name": "notion"},
                {"name": "substack"},
                {"name": "cli"},
                {"name": "meeting"},
                {"name": "db"},
                {"name": "external"},
            ]
        }
    },
    "Event Date": {"date": {}},
    "Last Reviewed": {"date": {}},
    "Reminder Date": {"date": {}},
    "Canonical Key": {"rich_text": {}},
    "Summary": {"rich_text": {}},
    "Decision Summary": {"rich_text": {}},
    "Action Items": {"rich_text": {}},
    "Lessons Learned": {"rich_text": {}},
    "Failure Pattern": {"multi_select": {"options": []}},
    "Parent Ref": {"rich_text": {}},
    "DB Record Ref": {"rich_text": {}},
    "URL": {"url": {}},
    "LLM Ready": {"checkbox": {}},
    "Historical Value": {
        "select": {
            "options": [
                {"name": "high"},
                {"name": "medium"},
                {"name": "low"},
            ]
        }
    },
    "Confidentiality": {
        "select": {
            "options": [
                {"name": "internal"},
                {"name": "exec_only"},
                {"name": "public"},
            ]
        }
    },
}


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def main() -> int:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_API_KEY or NOTION_DATABASE_ID missing")

    resp = httpx.patch(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}",
        headers=_headers(),
        json={"properties": ARCHIVE_PROPERTIES},
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    print(
        json.dumps(
            {
                "database_id": data.get("id"),
                "property_count": len(data.get("properties") or {}),
                "properties": sorted((data.get("properties") or {}).keys()),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
