"""Backfill legacy Notion archive pages with new schema properties.

Targets pages where Artifact Type is empty. Infers metadata from
existing fields (소스, 발행일, 제목) and applies sensible defaults.

Usage:
    python3 scripts/notion_backfill.py [--dry-run] [--limit N]
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from scripts.notion_canonical import normalize_project

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").split("?")[0]
NOTION_VERSION = "2022-06-28"

# Sources produced by the pipeline → issue_archive
_PIPELINE_SOURCES = {
    "arxiv_robotics", "arxiv_ai", "arxiv", "ieee_spectrum", "mit_tech_review",
    "boston_dynamics", "ieee", "mit", "techcrunch", "wired",
    "arXiv_robotics", "arXiv_AI", "Boston_Dynamics", "IEEE_Spectrum", "MIT_Tech_Review",
}


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _get_text(page: dict, prop: str) -> str:
    try:
        p = page["properties"][prop]
        ptype = p.get("type", "")
        if ptype == "title":
            items = p.get("title", [])
        elif ptype == "rich_text":
            items = p.get("rich_text", [])
        else:
            return ""
        return items[0]["text"]["content"] if items else ""
    except (KeyError, IndexError):
        return ""


def _infer_artifact_type(source: str, title: str) -> str:
    src_lower = source.lower()
    if any(s.lower() in src_lower for s in _PIPELINE_SOURCES):
        return "issue_archive"
    title_lower = title.lower()
    if any(k in title_lower for k in ("weekly", "issue #", "발행", "뉴스레터")):
        return "issue_archive"
    if any(k in title_lower for k in ("memo", "strategy", "전략")):
        return "strategy_memo"
    if any(k in title_lower for k in ("report", "리포트", "research")):
        return "research_report"
    if any(k in title_lower for k in ("decision", "결정", "승인")):
        return "decision_card"
    return "issue_archive"  # safe default for pipeline content


def _infer_teams(artifact_type: str) -> list[str]:
    if artifact_type in ("issue_archive", "research_report"):
        return ["Engineering", "QA"]
    if artifact_type in ("strategy_memo", "decision_card"):
        return ["Chief of Staff"]
    if artifact_type == "ops_brief":
        return ["Business Operations"]
    return ["Engineering"]


def _build_patch(page: dict, page_index: int) -> dict[str, Any]:
    title = _get_text(page, "제목")
    source = _get_text(page, "소스")
    page_id = page["id"].replace("-", "")[:8]

    artifact_type = _infer_artifact_type(source, title)
    teams = _infer_teams(artifact_type)
    project = normalize_project("Physical AI Weekly") if artifact_type == "issue_archive" else None

    props: dict[str, Any] = {
        "Artifact Type": {"select": {"name": artifact_type}},
        "Team": {"multi_select": [{"name": t} for t in teams]},
        "LLM Ready": {"checkbox": True},
        "Historical Value": {"select": {"name": "medium"}},
        "Confidentiality": {"select": {"name": "internal"}},
        "Project Status": {"select": {"name": "done"}},
        "Outcome": {"select": {"name": "success"}},
        "Source Channel": {"select": {"name": "db"}},
        "Canonical Key": {"rich_text": [{"text": {"content": f"{artifact_type}-backfill-{page_id}"}}]},
    }
    if project:
        props["Project"] = {"rich_text": [{"text": {"content": project}}]}

    return props


def _query_untyped(limit: int) -> list[dict]:
    payload = {
        "filter": {"property": "Artifact Type", "select": {"is_empty": True}},
        "page_size": min(limit, 100),
    }
    resp = httpx.post(
        f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
        headers=_headers(),
        json=payload,
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])[:limit]


def _patch_page(page_id: str, properties: dict) -> None:
    httpx.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=_headers(),
        json={"properties": properties},
        timeout=10.0,
    ).raise_for_status()


def run(dry_run: bool = False, limit: int = 100) -> dict[str, int]:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_API_KEY or NOTION_DATABASE_ID missing")

    pages = _query_untyped(limit)
    print(f"backfill 대상: {len(pages)}건 (dry_run={dry_run})")

    updated = 0
    failed = 0
    for i, page in enumerate(pages):
        title = _get_text(page, "제목")
        patch = _build_patch(page, i)
        artifact_type = patch["Artifact Type"]["select"]["name"]
        print(f"  [{i+1}/{len(pages)}] {artifact_type:15} | {title[:55]}")

        if not dry_run:
            try:
                _patch_page(page["id"], patch)
                updated += 1
                time.sleep(0.35)  # Notion rate limit ~3 req/s
            except Exception as e:
                print(f"    [ERROR] {e}")
                failed += 1

    return {"total": len(pages), "updated": updated, "failed": failed, "dry_run": dry_run}


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill legacy Notion archive pages")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    result = run(dry_run=args.dry_run, limit=args.limit)
    print(f"\n완료: {result}")
    return 0 if result.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
