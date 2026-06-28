#!/usr/bin/env python3
"""Audit and optionally fix edu RAG source/citation consistency.

Problem this guard blocks:
  refined_outputs.final_body is Tier 3 LLM synthesis. A sentence extracted from
  that synthesis must not be attributed to raw_signals.raw_data.url as if it
  appeared in the original source.

This script checks pipeline/refined RAG items in evidence_index.json and
evidence_bank.json. If an item has a refined_output_id, its cite must be
supported by source-owned raw text fields from the linked raw_signals row.
Unsupported items are reported, and with --fix removed from the RAG artifact and
written to a DLQ jsonl file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(PROJECT_ROOT / ".env", override=True)

from core.database import execute_query  # noqa: E402

EDU_DIR = PROJECT_ROOT / "data" / "edu_research"
INDEX_PATH = EDU_DIR / "evidence_index.json"
BANK_PATH = EDU_DIR / "evidence_bank.json"
DLQ_PATH = EDU_DIR / "evidence_source_consistency_dlq.jsonl"


def _normalize(text: str) -> str:
    return re.sub(r"[\s\"'‘’“”`·,;:!?().\[\]{}<>《》〈〉~…\-_/|]+", "", str(text or "").lower())


def _refined_output_id(item: dict[str, Any]) -> str:
    direct = str(item.get("refined_output_id") or "").strip()
    if direct.isdigit():
        return direct
    match = re.match(r"fresh-(\d+)(?:-\d+)?$", str(item.get("id") or ""))
    return match.group(1) if match else ""


def _raw_text_from_raw_data(raw_data: Any, full_content: str = "") -> str:
    if isinstance(raw_data, str):
        try:
            raw_data = json.loads(raw_data)
        except json.JSONDecodeError:
            raw_data = None
    parts: list[str] = []
    if isinstance(raw_data, dict):
        for key in ("full_content", "description", "summary", "abstract", "content", "transcript", "title"):
            value = str(raw_data.get(key) or "").strip()
            if value:
                parts.append(value)
    if full_content:
        parts.append(str(full_content))
    return " ".join(parts)


def _fetch_raw_text(refined_ids: set[str]) -> dict[str, str]:
    if not refined_ids:
        return {}
    ids = sorted(int(value) for value in refined_ids if value.isdigit())
    rows = execute_query(
        """
        SELECT ro.id AS refined_output_id, rs.raw_data, rs.full_content
        FROM refined_outputs ro
        JOIN filtered_signals fs ON fs.id = ro.filtered_signal_id
        JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        WHERE ro.id = ANY(%s)
        """,
        (ids,),
        fetch=True,
    ) or []
    result: dict[str, str] = {}
    for row in rows:
        rid = str(row.get("refined_output_id") or "")
        result[rid] = _raw_text_from_raw_data(row.get("raw_data"), str(row.get("full_content") or ""))
    return result


def _load_items(path: Path) -> tuple[Any, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = data.get("items") or []
    elif isinstance(data, list):
        items = data
    else:
        items = []
    return data, [item for item in items if isinstance(item, dict)]


def _save_items(path: Path, data: Any, items: list[dict[str, Any]]) -> None:
    if isinstance(data, dict):
        data["items"] = items
        if "count" in data:
            data["count"] = len(items)
        data["source_consistency_checked_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        data = items
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _is_supported(item: dict[str, Any], raw_text_by_refined: dict[str, str]) -> tuple[bool, str]:
    if str(item.get("provenance") or "").strip() == "anchor":
        return True, ""
    rid = _refined_output_id(item)
    if not rid:
        return True, ""
    cite = str(item.get("cite") or item.get("body") or "").strip()
    if len(cite) < 20:
        return False, "cite_too_short"
    raw_text = raw_text_by_refined.get(rid, "")
    if not raw_text:
        return False, "missing_source_raw_text"
    cite_norm = _normalize(cite)
    raw_norm = _normalize(raw_text)
    if cite_norm in raw_norm:
        return True, ""
    compact = cite_norm[:120]
    if len(compact) >= 40 and compact in raw_norm:
        return True, ""
    return False, "cite_not_supported_by_source"


def audit_path(path: Path, *, fix: bool, dlq_records: list[dict[str, Any]]) -> dict[str, Any]:
    data, items = _load_items(path)
    refined_ids = {_refined_output_id(item) for item in items if _refined_output_id(item)}
    raw_text_by_refined = _fetch_raw_text(refined_ids)
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for item in items:
        ok, reason = _is_supported(item, raw_text_by_refined)
        if ok:
            kept.append(item)
            continue
        record = {
            "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "artifact": str(path.relative_to(PROJECT_ROOT)),
            "reason": reason,
            "id": item.get("id"),
            "refined_output_id": _refined_output_id(item),
            "source": item.get("source"),
            "source_url": item.get("source_url") or item.get("source_ref"),
            "cite": item.get("cite"),
        }
        rejected.append(record)
        dlq_records.append(record)
    if fix and rejected:
        _save_items(path, data, kept)
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "total": len(items),
        "kept": len(kept),
        "rejected": len(rejected),
        "fixed": bool(fix),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Remove unsupported items and write DLQ records")
    parser.add_argument("--paths", nargs="*", default=[str(INDEX_PATH), str(BANK_PATH)])
    args = parser.parse_args()

    dlq_records: list[dict[str, Any]] = []
    reports = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            reports.append({"path": str(path), "missing": True})
            continue
        reports.append(audit_path(path, fix=args.fix, dlq_records=dlq_records))
    if args.fix and dlq_records:
        with DLQ_PATH.open("a", encoding="utf-8") as fh:
            for record in dlq_records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({
        "ok": True,
        "reports": reports,
        "dlq_appended": len(dlq_records) if args.fix else 0,
        "dlq_candidates": len(dlq_records),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
