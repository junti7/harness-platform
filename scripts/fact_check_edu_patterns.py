#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "runtime" / "edu_pattern_intelligence.json"
OUTPUT_PATH = ROOT / "runtime" / "edu_pattern_fact_check.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _status_for_pattern(pattern: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    support = int(pattern.get("supporting_evidence_count") or 0)
    distinct_sources = int(pattern.get("distinct_source_types") or 0)
    source_types = set(pattern.get("source_types") or [])
    complaints = int(pattern.get("complaint_count") or 0)
    score = float(pattern.get("pattern_score") or 0.0)

    if support < 2:
        reasons.append("supporting_evidence_count < 2")
    if distinct_sources < 2:
        reasons.append("distinct_source_types < 2")
    if "research_policy" not in source_types and "transcript" not in source_types:
        reasons.append("research_policy or transcript support missing")
    if score < 2.5:
        reasons.append("pattern_score < 2.5")
    if complaints > 0 and support == complaints:
        reasons.append("all support is complaint-driven")

    if not reasons:
        return "supported", ["minimum support, source diversity, and score thresholds passed"]
    if support >= 2 and score >= 2.5:
        return "weakly_supported", reasons
    if support == 0:
        return "needs_more_data", ["no supporting evidence"]
    return "needs_more_data", reasons


def build_fact_check() -> dict[str, Any]:
    payload = _load_json(INPUT_PATH)
    patterns = payload.get("patterns") or []
    results = []
    for pattern in patterns:
        status, reasons = _status_for_pattern(pattern)
        results.append(
            {
                "pattern_id": pattern.get("pattern_id"),
                "label": pattern.get("label"),
                "segment": pattern.get("segment"),
                "status": status,
                "reasons": reasons,
                "metrics": {
                    "supporting_evidence_count": pattern.get("supporting_evidence_count"),
                    "distinct_source_types": pattern.get("distinct_source_types"),
                    "source_types": pattern.get("source_types"),
                    "pattern_score": pattern.get("pattern_score"),
                    "complaint_count": pattern.get("complaint_count"),
                },
            }
        )
    summary = Counter(result["status"] for result in results)
    return {
        "generated_at": _now_iso(),
        "status": "ok" if payload else "missing_input",
        "input_path": str(INPUT_PATH.relative_to(ROOT)),
        "policy": {
            "minimum_supporting_evidence_count": 2,
            "minimum_distinct_source_types": 2,
            "required_anchor_support": "research_policy or transcript",
            "minimum_pattern_score": 2.5,
            "complaint_guard": "complaint-only support cannot auto-pass",
        },
        "summary": dict(summary),
        "patterns": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fact check the latest Edu pattern intelligence artifact.")
    parser.add_argument("--stdout", action="store_true", help="Print JSON to stdout.")
    parser.add_argument("--write", action="store_true", help="Write runtime artifact.")
    args = parser.parse_args()

    payload = build_fact_check()
    if args.write or not args.stdout:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stdout:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
