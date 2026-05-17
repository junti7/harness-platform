import argparse
import os
from datetime import date
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from scripts.send_notion_archive import markdown_to_notion_blocks
from scripts.notion_canonical import normalize_project, validate_archive_entry

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").split("?")[0]
NOTION_VERSION = "2022-06-28"
_NOTION_BLOCKS_PAGE_SIZE = 100


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _rich_text(value: str | None) -> dict[str, Any]:
    return {"rich_text": [{"type": "text", "text": {"content": (value or "")[:2000]}}]}


def _select(value: str | None) -> dict[str, Any]:
    return {"select": {"name": value}} if value else {"select": None}


def _multi_select(values: list[str] | None) -> dict[str, Any]:
    return {"multi_select": [{"name": value[:100]} for value in (values or []) if value]}


def _append_blocks(page_id: str, blocks: list[dict]) -> None:
    """Append blocks in chunks to avoid Notion's 100-block limit per request."""
    for i in range(0, len(blocks), _NOTION_BLOCKS_PAGE_SIZE):
        chunk = blocks[i: i + _NOTION_BLOCKS_PAGE_SIZE]
        resp = httpx.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            headers=_headers(),
            json={"children": chunk},
            timeout=30.0,
        )
        resp.raise_for_status()


def create_archive_page(
    *,
    title: str,
    body_markdown: str,
    artifact_type: str,
    teams: list[str],
    project: str | None = None,
    goal_id: int | None = None,
    goal_metric: str | None = None,
    project_status: str | None = None,
    outcome: str | None = None,
    source_channel: str | None = None,
    event_date: str | None = None,
    last_reviewed: str | None = None,
    reminder_date: str | None = None,
    canonical_key: str | None = None,
    summary: str | None = None,
    decision_summary: str | None = None,
    action_items: str | None = None,
    lessons_learned: str | None = None,
    failure_patterns: list[str] | None = None,
    parent_ref: str | None = None,
    db_record_ref: str | None = None,
    url: str | None = None,
    llm_ready: bool = True,
    historical_value: str | None = "high",
    confidentiality: str | None = "internal",
    tags: list[str] | None = None,
    legacy_source: str | None = None,
    strict: bool = True,
) -> dict[str, Any]:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        raise RuntimeError("NOTION_API_KEY or NOTION_DATABASE_ID missing")

    # canonical project name
    project = normalize_project(project)

    # validation
    errors = validate_archive_entry(
        title=title,
        artifact_type=artifact_type,
        teams=teams,
        summary=summary,
        canonical_key=canonical_key,
        decision_summary=decision_summary,
        lessons_learned=lessons_learned,
        outcome=outcome,
        action_items=action_items,
    )
    if errors and strict:
        raise ValueError("Archive entry validation failed:\n" + "\n".join(f"  - {e}" for e in errors))
    elif errors:
        import warnings
        warnings.warn("Archive entry validation warnings:\n" + "\n".join(f"  - {e}" for e in errors))

    properties = {
        "제목": {"title": [{"type": "text", "text": {"content": title[:2000]}}]},
        "태그": _multi_select(tags),
        "소스": _rich_text(legacy_source or source_channel or artifact_type),
        "발행일": {"date": {"start": event_date or str(date.today())}},
        "본문": _rich_text(summary or body_markdown[:1900]),  # summary preferred; body in blocks
        "Artifact Type": _select(artifact_type),
        "Team": _multi_select(teams),
        "Project": _rich_text(project),
        "Goal ID": {"number": goal_id},
        "Goal Metric": _rich_text(goal_metric),
        "Project Status": _select(project_status),
        "Outcome": _select(outcome),
        "Source Channel": _select(source_channel),
        "Event Date": {"date": {"start": event_date}} if event_date else {"date": None},
        "Last Reviewed": {"date": {"start": last_reviewed}} if last_reviewed else {"date": None},
        "Reminder Date": {"date": {"start": reminder_date}} if reminder_date else {"date": None},
        "Canonical Key": _rich_text(canonical_key),
        "Summary": _rich_text(summary),
        "Decision Summary": _rich_text(decision_summary),
        "Action Items": _rich_text(action_items),
        "Lessons Learned": _rich_text(lessons_learned),
        "Failure Pattern": _multi_select(failure_patterns),
        "Parent Ref": _rich_text(parent_ref),
        "DB Record Ref": _rich_text(db_record_ref),
        "URL": {"url": url},
        "LLM Ready": {"checkbox": llm_ready},
        "Historical Value": _select(historical_value),
        "Confidentiality": _select(confidentiality),
    }

    all_blocks = markdown_to_notion_blocks(body_markdown)
    first_chunk = all_blocks[:_NOTION_BLOCKS_PAGE_SIZE]
    overflow = all_blocks[_NOTION_BLOCKS_PAGE_SIZE:]

    resp = httpx.post(
        "https://api.notion.com/v1/pages",
        headers=_headers(),
        json={
            "parent": {"database_id": NOTION_DATABASE_ID},
            "properties": properties,
            "children": first_chunk,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    page = resp.json()

    if overflow:
        _append_blocks(page["id"], overflow)

    return page


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive an operating artifact into the universal Notion archive.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--title")
    parser.add_argument("--artifact-type", required=True)
    parser.add_argument("--team", action="append", required=True)
    parser.add_argument("--project")
    parser.add_argument("--goal-id", type=int)
    parser.add_argument("--goal-metric")
    parser.add_argument("--project-status")
    parser.add_argument("--outcome")
    parser.add_argument("--source-channel")
    parser.add_argument("--event-date")
    parser.add_argument("--last-reviewed")
    parser.add_argument("--reminder-date")
    parser.add_argument("--canonical-key")
    parser.add_argument("--summary")
    parser.add_argument("--decision-summary")
    parser.add_argument("--action-items")
    parser.add_argument("--lessons-learned")
    parser.add_argument("--failure-pattern", action="append")
    parser.add_argument("--parent-ref")
    parser.add_argument("--db-record-ref")
    parser.add_argument("--url")
    parser.add_argument("--historical-value", default="high")
    parser.add_argument("--confidentiality", default="internal")
    parser.add_argument("--tag", action="append")
    parser.add_argument("--legacy-source")
    args = parser.parse_args()

    body = args.file.read_text(encoding="utf-8")
    result = create_archive_page(
        title=args.title or args.file.stem,
        body_markdown=body,
        artifact_type=args.artifact_type,
        teams=args.team,
        project=args.project,
        goal_id=args.goal_id,
        goal_metric=args.goal_metric,
        project_status=args.project_status,
        outcome=args.outcome,
        source_channel=args.source_channel,
        event_date=args.event_date,
        last_reviewed=args.last_reviewed,
        reminder_date=args.reminder_date,
        canonical_key=args.canonical_key,
        summary=args.summary,
        decision_summary=args.decision_summary,
        action_items=args.action_items,
        lessons_learned=args.lessons_learned,
        failure_patterns=args.failure_pattern,
        parent_ref=args.parent_ref,
        db_record_ref=args.db_record_ref,
        url=args.url,
        historical_value=args.historical_value,
        confidentiality=args.confidentiality,
        tags=args.tag,
        legacy_source=args.legacy_source,
    )
    print(result.get("url"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
