#!/usr/bin/env python3
"""Score privacy-safe production shadow telemetry without reading message text."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ALLOWED_KEYS = {
    "ts", "schema_version", "contract_schema", "task_type", "subject_bucket", "route_class",
    "adapter_ids", "authority_buckets", "coverage_buckets", "decision", "reason_codes",
    "evidence_count", "claim_count", "missing_dimension_count", "latency_ms",
}
FORBIDDEN_KEYS = {"request", "message", "text", "output", "payload", "evidence", "claim", "session_id", "requester_user_id"}
REQUIRED_TASK_TYPES = {"lookup", "status", "summary", "diagnose", "explain", "recommend", "transform", "action"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--min-days", type=int, default=7)
    parser.add_argument("--min-cases", type=int, default=200)
    parser.add_argument("--min-family-cases", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.input)
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()] if source.exists() else []
    failures: list[str] = []
    days = sorted({datetime.fromisoformat(row["ts"]).date().isoformat() for row in rows if row.get("ts")})
    families = Counter(str(row.get("task_type")) for row in rows)
    privacy_violations = [
        index for index, row in enumerate(rows, 1)
        if set(row) - ALLOWED_KEYS or set(row) & FORBIDDEN_KEYS
    ]
    invalid_decisions = [index for index, row in enumerate(rows, 1) if row.get("decision") not in {"deliver", "partial", "abstain"}]
    if len(days) < args.min_days:
        failures.append(f"observed_days={len(days)}<{args.min_days}")
    if len(rows) < args.min_cases:
        failures.append(f"cases={len(rows)}<{args.min_cases}")
    if privacy_violations:
        failures.append(f"privacy_schema_violations={len(privacy_violations)}")
    if invalid_decisions:
        failures.append(f"invalid_decisions={len(invalid_decisions)}")
    missing_families = sorted(REQUIRED_TASK_TYPES - set(families))
    thin_families = sorted(family for family in REQUIRED_TASK_TYPES if families[family] < args.min_family_cases)
    if missing_families:
        failures.append(f"missing_task_types={','.join(missing_families)}")
    if thin_families:
        failures.append(f"family_minimum_not_met={','.join(thin_families)}")

    report = {
        "schema_version": "1.0",
        "input": args.input,
        "observed_days": days,
        "case_count": len(rows),
        "family_counts": dict(families),
        "privacy_schema_violations": privacy_violations,
        "invalid_decisions": invalid_decisions,
        "failures": failures,
        "status": "pass" if not failures else "blocked",
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "cases": len(rows), "days": len(days), "failures": failures}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
