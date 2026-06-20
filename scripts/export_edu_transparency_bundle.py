#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]

from core.database import execute_query

EXPECTED_TABLES = {
    "edu_knowledge_items": {
        "owner": "P1 normalized knowledge store",
        "source_of_truth": "infra/migrations/2026-06-14_edu_query_engine_p1.sql",
    },
    "dead_letter_queue": {
        "owner": "ingestion failure queue",
        "source_of_truth": "infra/schema.sql + infra/migrations/2026-06-14_edu_query_engine_p1.sql",
    },
    "pipeline_runs": {
        "owner": "ingestion audit log",
        "source_of_truth": "infra/schema.sql + infra/migrations/2026-06-14_edu_query_engine_p1.sql",
    },
    "edu_rag_accumulation": {
        "owner": "grounded answer accumulation",
        "source_of_truth": "infra/migrations/2026-06-14_edu_query_engine_p1.sql",
    },
}

EXPECTED_VIEWS = {
    "edu_knowledge_items_customer_facing": {
        "owner": "canonical safe retrieval boundary",
        "source_of_truth": "infra/migrations/2026-06-14_edu_query_engine_p1.sql",
    }
}

QUERY_PATHS = [
    {
        "stage": "ingestion",
        "file": "scripts/edu_data_analysis_agent.py",
        "functions": ["_upsert_knowledge_items", "_write_dlq", "_mark_pipeline_success_in_tx", "_run_db_persist"],
        "sql_targets": ["edu_knowledge_items", "dead_letter_queue", "pipeline_runs"],
    },
    {
        "stage": "customer_facing_retrieval",
        "file": "harness-os/backend/main.py",
        "functions": ["_edu_query_text", "_retrieve_evidence_bundle", "_edu_db_customer_facing_bundle"],
        "sql_targets": ["edu_knowledge_items_customer_facing"],
    },
    {
        "stage": "fallback_retrieval",
        "file": "harness-os/backend/main.py",
        "functions": ["_edu_ranked_matches", "_load_rag_index"],
        "sql_targets": ["data/edu_research/evidence_index.json"],
    },
]


def _safe_query(query: str, params: tuple[Any, ...] | None = None) -> list[dict[str, Any]] | None:
    try:
        return execute_query(query, params, fetch=True)
    except Exception:
        return None


def _list_tables() -> list[str]:
    rows = _safe_query(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND (table_name LIKE 'edu_%' OR table_name IN ('dead_letter_queue', 'pipeline_runs'))
        ORDER BY table_name
        """
    ) or []
    return [str(row["table_name"]) for row in rows]


def _list_views() -> list[str]:
    rows = _safe_query(
        """
        SELECT viewname
        FROM pg_views
        WHERE schemaname = 'public'
          AND viewname LIKE 'edu_%'
        ORDER BY viewname
        """
    ) or []
    return [str(row["viewname"]) for row in rows]


def _columns(name: str) -> list[dict[str, Any]]:
    return _safe_query(
        """
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (name,),
    ) or []


def _indexes(name: str) -> list[dict[str, Any]]:
    return _safe_query(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = %s
        ORDER BY indexname
        """,
        (name,),
    ) or []


def _row_count(name: str) -> int | None:
    rows = _safe_query(f"SELECT count(*) AS c FROM {name}")
    if not rows:
        return None
    return int(rows[0]["c"])


def _sample_rows(name: str, limit: int = 5) -> list[dict[str, Any]] | None:
    return _safe_query(f"SELECT * FROM {name} ORDER BY 1 DESC LIMIT {limit}")


def _all_rows(name: str) -> list[dict[str, Any]] | None:
    return _safe_query(f"SELECT * FROM {name} ORDER BY 1 DESC")


def _view_definition(name: str) -> str | None:
    rows = _safe_query(
        """
        SELECT definition
        FROM pg_views
        WHERE schemaname = 'public' AND viewname = %s
        """,
        (name,),
    )
    if not rows:
        return None
    return str(rows[0]["definition"])


def _latest_pipeline_runs(limit: int = 10) -> list[dict[str, Any]] | None:
    return _safe_query(
        """
        SELECT *
        FROM pipeline_runs
        ORDER BY id DESC
        LIMIT %s
        """,
        (limit,),
    )


def _latest_dlq(limit: int = 10) -> list[dict[str, Any]] | None:
    return _safe_query(
        """
        SELECT *
        FROM dead_letter_queue
        ORDER BY id DESC
        LIMIT %s
        """,
        (limit,),
    )


def _dlq_reason_summary() -> list[dict[str, Any]] | None:
    return _safe_query(
        """
        SELECT reason_code, count(*) AS c
        FROM dead_letter_queue
        GROUP BY reason_code
        ORDER BY c DESC, reason_code
        """
    )


def _filesystem_inventory() -> dict[str, Any]:
    research_files = sorted((ROOT / "data" / "edu_research").rglob("*"))
    transcript_files = sorted((ROOT / "data" / "edu_youtube_transcripts").rglob("*"))
    return {
        "edu_research_files": sum(1 for path in research_files if path.is_file()),
        "edu_youtube_transcript_files": sum(1 for path in transcript_files if path.is_file()),
        "anchors_exists": (ROOT / "data" / "edu_research" / "evidence_anchors.json").exists(),
        "evidence_index_exists": (ROOT / "data" / "edu_research" / "evidence_index.json").exists(),
    }


def _customer_facing_sql() -> str:
    return """
SELECT
    id,
    source,
    source_kind,
    segment,
    item_type AS type,
    title,
    body,
    cite,
    quality_score,
    rights_class,
    excerpt_max_chars,
    verbatim_allowed,
    keywords
FROM edu_knowledge_items_customer_facing
WHERE COALESCE(segment, '') IN ('', :segment)
ORDER BY
    CASE WHEN segment = :segment THEN 0 ELSE 1 END,
    quality_score DESC,
    id DESC
LIMIT :limit
""".strip()


def _excel_column_name(index: int) -> str:
    value = index + 1
    chars: list[str] = []
    while value:
        value, remainder = divmod(value - 1, 26)
        chars.append(chr(65 + remainder))
    return "".join(reversed(chars))


def _xlsx_cell_xml(row_idx: int, col_idx: int, value: Any) -> str:
    cell_ref = f"{_excel_column_name(col_idx)}{row_idx}"
    if value is None:
        return f'<c r="{cell_ref}"/>'
    if isinstance(value, bool):
        return f'<c r="{cell_ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, int) and not isinstance(value, bool):
        return f'<c r="{cell_ref}"><v>{value}</v></c>'
    if isinstance(value, float):
        if value != value or value in {float("inf"), float("-inf")}:
            text = ""
        else:
            return f'<c r="{cell_ref}"><v>{value}</v></c>'
    else:
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False)
        else:
            text = str(value)
    text = escape(text)
    return f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def _worksheet_xml(rows: list[list[Any]]) -> str:
    xml_rows: list[str] = []
    for row_idx, row in enumerate(rows, start=1):
        cells = "".join(_xlsx_cell_xml(row_idx, col_idx, value) for col_idx, value in enumerate(row))
        xml_rows.append(f'<row r="{row_idx}">{cells}</row>')
    sheet_data = "".join(xml_rows)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{sheet_data}</sheetData>"
        "</worksheet>"
    )


def build_object_xlsx(name: str) -> bytes:
    safe_name = str(name or "").strip()
    if not safe_name:
        raise ValueError("object name required")
    obj_type = "view" if safe_name in EXPECTED_VIEWS else "table"
    exists_rows = execute_query(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        ) AS exists_table,
        EXISTS (
            SELECT 1
            FROM pg_views
            WHERE schemaname = 'public' AND viewname = %s
        ) AS exists_view
        """,
        (safe_name, safe_name),
        fetch=True,
    )
    exists = bool(exists_rows and (exists_rows[0]["exists_table"] or exists_rows[0]["exists_view"]))
    if not exists:
        raise ValueError(f"object not found: {safe_name}")

    owner = (EXPECTED_TABLES.get(safe_name) or EXPECTED_VIEWS.get(safe_name) or {}).get("owner")
    source_of_truth = (EXPECTED_TABLES.get(safe_name) or EXPECTED_VIEWS.get(safe_name) or {}).get("source_of_truth")
    row_count = _row_count(safe_name)
    columns = _columns(safe_name)
    rows = _all_rows(safe_name) or []
    row_columns = list(rows[0].keys()) if rows else [col["column_name"] for col in columns]

    meta_sheet = [
        ["field", "value"],
        ["name", safe_name],
        ["type", obj_type],
        ["exists", exists],
        ["expected", safe_name in EXPECTED_TABLES or safe_name in EXPECTED_VIEWS],
        ["owner", owner or ""],
        ["source_of_truth", source_of_truth or ""],
        ["row_count", row_count if row_count is not None else ""],
        ["exported_at_utc", datetime.now(timezone.utc).isoformat(timespec="seconds")],
    ]
    columns_sheet = [["idx", "column_name", "data_type", "is_nullable"]]
    for index, column in enumerate(columns):
        columns_sheet.append([index, column.get("column_name"), column.get("data_type"), column.get("is_nullable")])
    rows_sheet = [row_columns]
    for row in rows:
        rows_sheet.append([row.get(column) for column in row_columns])

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        '<sheet name="meta" sheetId="1" r:id="rId1"/>'
        '<sheet name="columns" sheetId="2" r:id="rId2"/>'
        '<sheet name="rows" sheetId="3" r:id="rId3"/>'
        "</sheets>"
        "</workbook>"
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>'
        "</Relationships>"
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        zf.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(meta_sheet))
        zf.writestr("xl/worksheets/sheet2.xml", _worksheet_xml(columns_sheet))
        zf.writestr("xl/worksheets/sheet3.xml", _worksheet_xml(rows_sheet))
    return buffer.getvalue()


def build_bundle() -> dict[str, Any]:
    actual_tables = _list_tables()
    actual_views = _list_views()
    expected_table_names = sorted(EXPECTED_TABLES.keys())
    expected_view_names = sorted(EXPECTED_VIEWS.keys())
    table_details = {}
    for name in sorted(set(actual_tables) | set(expected_table_names)):
        table_details[name] = {
            "exists": name in actual_tables,
            "expected": name in EXPECTED_TABLES,
            "owner": EXPECTED_TABLES.get(name, {}).get("owner"),
            "source_of_truth": EXPECTED_TABLES.get(name, {}).get("source_of_truth"),
            "row_count": _row_count(name) if name in actual_tables else None,
            "columns": _columns(name) if name in actual_tables else [],
            "indexes": _indexes(name) if name in actual_tables else [],
            "sample_rows": _sample_rows(name) if name in actual_tables else None,
        }
    view_details = {}
    for name in sorted(set(actual_views) | set(expected_view_names)):
        view_details[name] = {
            "exists": name in actual_views,
            "expected": name in EXPECTED_VIEWS,
            "owner": EXPECTED_VIEWS.get(name, {}).get("owner"),
            "source_of_truth": EXPECTED_VIEWS.get(name, {}).get("source_of_truth"),
            "row_count": _row_count(name) if name in actual_views else None,
            "definition": _view_definition(name) if name in actual_views else None,
            "sample_rows": _sample_rows(name) if name in actual_views else None,
        }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "filesystem_inventory": _filesystem_inventory(),
        "expected_tables": expected_table_names,
        "actual_tables": actual_tables,
        "missing_expected_tables": [name for name in expected_table_names if name not in actual_tables],
        "unexpected_tables": [name for name in actual_tables if name not in expected_table_names],
        "expected_views": expected_view_names,
        "actual_views": actual_views,
        "missing_expected_views": [name for name in expected_view_names if name not in actual_views],
        "query_paths": QUERY_PATHS,
        "customer_facing_query_sql": _customer_facing_sql(),
        "tables": table_details,
        "views": view_details,
        "latest_pipeline_runs": _latest_pipeline_runs(),
        "latest_dead_letter_queue": _latest_dlq(),
        "dead_letter_queue_reason_summary": _dlq_reason_summary(),
    }


def render_markdown(bundle: dict[str, Any]) -> str:
    lines = [
        "# Edu Full Transparency Bundle",
        "",
        f"- generated_at: `{bundle['generated_at']}`",
        f"- expected_tables: `{', '.join(bundle['expected_tables'])}`",
        f"- actual_tables: `{', '.join(bundle['actual_tables']) if bundle['actual_tables'] else '(none)'}`",
        f"- missing_expected_tables: `{', '.join(bundle['missing_expected_tables']) if bundle['missing_expected_tables'] else '(none)'}`",
        f"- expected_views: `{', '.join(bundle['expected_views'])}`",
        f"- actual_views: `{', '.join(bundle['actual_views']) if bundle['actual_views'] else '(none)'}`",
        f"- missing_expected_views: `{', '.join(bundle['missing_expected_views']) if bundle['missing_expected_views'] else '(none)'}`",
        "",
        "## Filesystem Inventory",
        "",
    ]
    for key, value in bundle["filesystem_inventory"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend([
        "",
        "## Query Path",
        "",
    ])
    for path in bundle["query_paths"]:
        lines.append(f"- stage: `{path['stage']}`")
        lines.append(f"  file: `{path['file']}`")
        lines.append(f"  functions: `{', '.join(path['functions'])}`")
        lines.append(f"  targets: `{', '.join(path['sql_targets'])}`")
    lines.extend([
        "",
        "## Customer-Facing SQL",
        "",
        "```sql",
        bundle["customer_facing_query_sql"],
        "```",
        "",
    ])
    for name, info in bundle["tables"].items():
        lines.extend([
            f"## Table: {name}",
            "",
            f"- exists: `{info['exists']}`",
            f"- expected: `{info['expected']}`",
            f"- owner: `{info['owner']}`",
            f"- source_of_truth: `{info['source_of_truth']}`",
            f"- row_count: `{info['row_count']}`",
            "- columns:",
        ])
        for col in info["columns"]:
            lines.append(f"  - `{col['column_name']}` `{col['data_type']}` nullable=`{col['is_nullable']}`")
        lines.append("- indexes:")
        for idx in info["indexes"]:
            lines.append(f"  - `{idx['indexname']}`")
        lines.append("")
    for name, info in bundle["views"].items():
        lines.extend([
            f"## View: {name}",
            "",
            f"- exists: `{info['exists']}`",
            f"- expected: `{info['expected']}`",
            f"- owner: `{info['owner']}`",
            f"- source_of_truth: `{info['source_of_truth']}`",
            f"- row_count: `{info['row_count']}`",
        ])
        if info["definition"]:
            lines.extend(["```sql", info["definition"], "```"])
        lines.append("")
    lines.extend([
        "## Latest Pipeline Runs",
        "",
        "```json",
        json.dumps(bundle["latest_pipeline_runs"], ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## Latest DLQ Rows",
        "",
        "```json",
        json.dumps(bundle["latest_dead_letter_queue"], ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## DLQ Reason Summary",
        "",
        "```json",
        json.dumps(bundle["dead_letter_queue_reason_summary"], ensure_ascii=False, indent=2, default=str),
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    bundle = build_bundle()
    out_dir = ROOT / "docs" / "reviews" / "edu_db_transparency"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    json_path = out_dir / f"edu_db_transparency_{stamp}.json"
    md_path = out_dir / f"edu_db_transparency_{stamp}.md"
    latest_json = out_dir / "latest.json"
    latest_md = out_dir / "latest.md"
    json_payload = json.dumps(bundle, ensure_ascii=False, indent=2, default=str) + "\n"
    md_payload = render_markdown(bundle)
    json_path.write_text(json_payload, encoding="utf-8")
    md_path.write_text(md_payload, encoding="utf-8")
    latest_json.write_text(json_payload, encoding="utf-8")
    latest_md.write_text(md_payload, encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "missing_expected_tables": bundle["missing_expected_tables"],
        "missing_expected_views": bundle["missing_expected_views"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
