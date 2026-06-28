#!/usr/bin/env python3
"""Backfill source_url metadata into existing edu RAG artifacts.

This is metadata-only: it does not regenerate embeddings. It recovers URLs from
raw_signals.raw_data for pipeline items and from evidence_anchors.json for
evergreen anchors.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env", override=True)

from core.database import execute_query  # noqa: E402
from scripts.refresh_edu_evidence_bank import EDU_DIR, extract_source_url  # noqa: E402

INDEX_PATH = EDU_DIR / "evidence_index.json"
BANK_PATH = EDU_DIR / "evidence_bank.json"
ANCHORS_PATH = EDU_DIR / "evidence_anchors.json"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("items")
        return items if isinstance(items, list) else []
    return payload if isinstance(payload, list) else []


def _refined_output_id(item: dict[str, Any]) -> str:
    direct = str(item.get("refined_output_id") or "").strip()
    if direct.isdigit():
        return direct
    match = re.match(r"fresh-(\d+)(?:-\d+)?$", str(item.get("id") or ""))
    return match.group(1) if match else ""


def _anchor_url_map() -> dict[str, str]:
    try:
        anchors = _items(_read_json(ANCHORS_PATH))
    except Exception:
        return {}
    return {
        str(item.get("id") or ""): str(item.get("source_url") or item.get("url") or item.get("link") or "").strip()
        for item in anchors
        if str(item.get("source_url") or item.get("url") or item.get("link") or "").strip()
    }


def _raw_url_map(refined_ids: set[str]) -> dict[str, dict[str, str]]:
    ids = sorted({int(value) for value in refined_ids if str(value).isdigit()})
    if not ids:
        return {}
    out: dict[str, dict[str, str]] = {}
    batch_size = 300
    for start in range(0, len(ids), batch_size):
        batch = ids[start : start + batch_size]
        placeholders = ", ".join(["%s"] * len(batch))
        rows = execute_query(
            f"""
            SELECT ro.id, rs.source, rs.raw_data
            FROM refined_outputs ro
            JOIN filtered_signals fs ON fs.id = ro.filtered_signal_id
            JOIN raw_signals rs ON rs.id = fs.raw_signal_id
            WHERE ro.id IN ({placeholders})
            """,
            tuple(batch),
            fetch=True,
        ) or []
        for row in rows:
            rid = str(row.get("id") or "")
            url = extract_source_url(row.get("raw_data"))
            out[rid] = {
                "source_url": url,
                "source_name": str(row.get("source") or ""),
            }
    return out


def _backfill_path(path: Path, anchor_urls: dict[str, str], raw_urls: dict[str, dict[str, str]]) -> dict[str, int]:
    payload = _read_json(path)
    items = _items(payload)
    changed = 0
    recovered = 0
    still_missing = 0
    for item in items:
        existing_url = str(item.get("source_url") or item.get("url") or item.get("link") or "").strip()
        resolved_url = existing_url
        source_name = ""
        item_id = str(item.get("id") or "")
        if not resolved_url and item_id in anchor_urls:
            resolved_url = anchor_urls[item_id]
        rid = _refined_output_id(item)
        if not resolved_url and rid in raw_urls:
            resolved_url = raw_urls[rid].get("source_url") or ""
            source_name = raw_urls[rid].get("source_name") or ""
        if resolved_url:
            if item.get("source_url") != resolved_url:
                item["source_url"] = resolved_url
                changed += 1
            source_ref = str(item.get("source_ref") or "").strip()
            if not source_ref or not source_ref.startswith(("http://", "https://")):
                item["source_ref"] = resolved_url
                changed += 1
            if rid and not item.get("refined_output_id"):
                item["refined_output_id"] = int(rid)
                changed += 1
            if source_name and not item.get("source_name"):
                item["source_name"] = source_name
                changed += 1
            recovered += 1
        else:
            still_missing += 1
    if changed:
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return {"items": len(items), "changed_fields": changed, "url_present": recovered, "still_missing": still_missing}


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill edu RAG source_url metadata without re-embedding.")
    parser.add_argument("--dry-run", action="store_true", help="count only; do not write files")
    args = parser.parse_args()

    paths = [p for p in (INDEX_PATH, BANK_PATH) if p.exists()]
    refined_ids: set[str] = set()
    for path in paths:
        for item in _items(_read_json(path)):
            rid = _refined_output_id(item)
            if rid:
                refined_ids.add(rid)
    anchor_urls = _anchor_url_map()
    raw_urls = _raw_url_map(refined_ids)

    results: dict[str, Any] = {
        "anchor_url_count": len(anchor_urls),
        "raw_url_count": sum(1 for value in raw_urls.values() if value.get("source_url")),
        "files": {},
    }
    if args.dry_run:
        print(json.dumps(results, ensure_ascii=False))
        return 0
    for path in paths:
        results["files"][str(path.relative_to(PROJECT_ROOT))] = _backfill_path(path, anchor_urls, raw_urls)
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
