#!/usr/bin/env python3
"""Build a reproducible, parent-only evidence slice from raw_signals.

This is intentionally conservative: it excludes adult/B2B/investment themes,
deduplicates by content_hash, and emits only source metadata plus paraphrase
seeds. It never turns a raw item into a factual claim automatically.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import subprocess

OUT = Path("docs/reports/evidence/ai_career_parent_evidence_slice_20260718.json")
DB = os.environ.get("DATABASE_URL", "postgresql://localhost/harness_dev")
PARENT = re.compile(r"(학부모|부모|자녀|아이|학생|중학생|청소년|초등|고등학생|학원|사교육|진학|진로)", re.I)
TOPIC = re.compile(r"(AI|인공지능|챗GPT|로봇|코딩|프로그래밍|프로젝트|데이터|공학|디지털)", re.I)
EXCLUDE = re.compile(r"(직장인|재취업|로스쿨|대학원|B2B|기업교육|투자|주식|매출|구독자|노인|시니어)", re.I)


def main() -> None:
    query = """
        SELECT json_build_array(
                 id, source, ingested_at, content_hash,
                 COALESCE(raw_data->>'title',''),
                 COALESCE(full_content, raw_data->>'content','')
               )::text
        FROM raw_signals
        WHERE domain = 'edu_consulting'
        ORDER BY ingested_at DESC NULLS LAST, id DESC
    """
    proc = subprocess.run(["psql", DB, "-At", "-c", query], check=True, capture_output=True, text=True)
    seen: set[str] = set()
    rows = []
    for line in proc.stdout.splitlines():
        try:
            fields = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(fields, list) or len(fields) < 6:
            continue
        ident, source, ingested_at, content_hash, title, body = fields[:6]
        text = f"{title} {body}".strip()
        if not PARENT.search(text) or not TOPIC.search(text) or EXCLUDE.search(text):
            continue
        digest = content_hash or hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        rows.append({
            "source_id": f"EDU-{ident}",
            "record_id": ident,
            "source": source,
            "ingested_at": ingested_at or None,
            "content_hash": digest,
            "title": title[:240],
            "paraphrase_seed": text[:500],
            "claim_status": "needs_human_claim_review"
        })
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_scope": "raw_signals.domain=edu_consulting",
        "include_regex": {"parent": PARENT.pattern, "topic": TOPIC.pattern},
        "exclude_regex": EXCLUDE.pattern,
        "unique_items": len(rows),
        "source_counts": {source: sum(1 for row in rows if row["source"] == source) for source in sorted({row["source"] for row in rows})},
        "evidence_patterns": [
            {"pattern_id": "E1", "rule": "parent context + AI topic", "count": len(rows), "interpretation": "candidate inventory only; not demand share"},
            {"pattern_id": "E2", "rule": "content_hash deduplication", "count": len(seen), "interpretation": "unique candidate count after dedup"},
            {"pattern_id": "E3", "rule": "adult/B2B/investment exclusion", "count": "applied", "interpretation": "scope control, not a quality guarantee"}
        ],
        "items": rows[:500],
        "note": "Items are evidence candidates, not verified claims. Human source locator and claim mapping are required before publication."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} unique candidates; capped output 500)")


if __name__ == "__main__":
    main()
