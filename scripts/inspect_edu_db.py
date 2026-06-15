#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from core.database import execute_query

TARGET_TABLES = [
    "edu_knowledge_items",
    "dead_letter_queue",
    "pipeline_runs",
    "edu_rag_accumulation",
]
TARGET_VIEWS = [
    "edu_knowledge_items_customer_facing",
]


def _columns(table_name: str) -> list[dict]:
    return execute_query(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
        fetch=True,
    )


def _indexes(table_name: str) -> list[dict]:
    return execute_query(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = %s
        ORDER BY indexname
        """,
        (table_name,),
        fetch=True,
    )


def _row_count(table_name: str) -> int | None:
    try:
        rows = execute_query(f"SELECT count(*) AS c FROM {table_name}", fetch=True)
        return int(rows[0]["c"]) if rows else 0
    except Exception:
        return None


def _view_definition(view_name: str) -> str:
    rows = execute_query(
        """
        SELECT definition
        FROM pg_views
        WHERE viewname = %s
        """,
        (view_name,),
        fetch=True,
    )
    return str(rows[0]["definition"]) if rows else ""


def build_report() -> dict:
    report = {
        "tables": {},
        "views": {},
    }
    for table in TARGET_TABLES:
        report["tables"][table] = {
            "row_count": _row_count(table),
            "columns": _columns(table),
            "indexes": _indexes(table),
        }
    for view in TARGET_VIEWS:
        report["views"][view] = {
            "row_count": _row_count(view),
            "definition": _view_definition(view),
        }
    return report


def render_markdown(report: dict) -> str:
    lines = [
        "# Edu DB Snapshot",
        "",
    ]
    for table, data in report["tables"].items():
        lines.extend(
            [
                f"## {table}",
                "",
                f"- row_count: `{data['row_count']}`",
                "- columns:",
            ]
        )
        for col in data["columns"]:
            lines.append(f"  - `{col['column_name']}`: `{col['data_type']}` nullable=`{col['is_nullable']}`")
        lines.append("- indexes:")
        for idx in data["indexes"]:
            lines.append(f"  - `{idx['indexname']}`")
        lines.append("")
    for view, data in report["views"].items():
        lines.extend(
            [
                f"## {view}",
                "",
                f"- row_count: `{data['row_count']}`",
                "```sql",
                data["definition"],
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
