#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "harness-os" / "backend" / "main.py"
POLICY_CANDIDATE_PATH = ROOT / "docs" / "reviews" / "edu_coach_simulations" / "policy_candidates.jsonl"


def _load_backend() -> Any:
    module_name = "harness_backend_main_for_edu_auto_reinforcement_report"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, BACKEND_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load backend module: {BACKEND_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def _count_policy_candidates(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = POLICY_CANDIDATE_PATH
    if not path.exists():
        return {"exists": False, "count": 0, "latest": []}
    rows: list[dict[str, Any]] = []
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            count += 1
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                parsed = {"parse_error": True, "raw": line[:500]}
            if isinstance(parsed, dict):
                rows.append(parsed)
                rows = rows[-5:]
    return {
        "exists": True,
        "count": count,
        "latest": [
            {
                "candidate_id": str(item.get("candidate_id") or ""),
                "highest_severity": str(item.get("highest_severity") or ""),
                "issues": item.get("issues") if isinstance(item.get("issues"), list) else [],
                "promotion_status": str(item.get("promotion_status") or ""),
                "created_at": str(item.get("created_at") or ""),
            }
            for item in rows
        ],
    }


def run_report(*, lookback_days: int = 7, sla_minutes: int = 5, pending_limit: int = 10) -> dict[str, Any]:
    backend = _load_backend()
    if hasattr(backend, "_ensure_edu_case_schema"):
        backend._ensure_edu_case_schema()
    safe_days = max(1, min(int(lookback_days or 7), 365))
    safe_sla = max(1, min(int(sla_minutes or 5), 1440))
    safe_limit = max(1, min(int(pending_limit or 10), 100))

    summary_rows = backend._edu_execute(
        """
        WITH downvotes AS (
          SELECT case_id, email, event_payload, created_at
          FROM edu_vp_training_event_log
          WHERE event_type = 'safety_coach_feedback'
            AND event_name = 'answer_feedback_recorded'
            AND event_payload->>'rating' = 'down'
            AND created_at >= NOW() - (%s || ' days')::INTERVAL
        ),
        matched AS (
          SELECT
            d.created_at AS downvote_created_at,
            MIN(r.created_at) AS review_created_at
          FROM downvotes d
          LEFT JOIN edu_vp_training_event_log r
            ON r.event_type = 'safety_coach_feedback'
           AND r.event_name = 'answer_auto_reinforcement_reviewed'
           AND r.case_id IS NOT DISTINCT FROM d.case_id
           AND r.email = d.email
           AND r.event_payload->>'question' = d.event_payload->>'question'
           AND r.event_payload->>'answer' = d.event_payload->>'answer'
           AND r.event_payload->>'feedback_saved_at' = d.event_payload->>'feedback_saved_at'
          GROUP BY d.case_id, d.email, d.event_payload, d.created_at
        )
        SELECT
          COUNT(*)::int AS downvote_count,
          COUNT(review_created_at)::int AS reviewed_count,
          COUNT(*) FILTER (WHERE review_created_at IS NULL)::int AS pending_count,
          COUNT(*) FILTER (
            WHERE review_created_at IS NOT NULL
              AND review_created_at <= downvote_created_at + (%s || ' minutes')::INTERVAL
          )::int AS reviewed_within_sla_count,
          COUNT(*) FILTER (
            WHERE review_created_at IS NULL
              AND downvote_created_at < NOW() - (%s || ' minutes')::INTERVAL
          )::int AS stale_pending_count,
          MAX(downvote_created_at) AS last_downvote_at,
          MAX(review_created_at) AS last_review_at
        FROM matched
        """,
        (str(safe_days), str(safe_sla), str(safe_sla)),
        fetch=True,
    )
    summary = dict(summary_rows[0]) if summary_rows else {}
    downvote_count = int(summary.get("downvote_count") or 0)
    reviewed_count = int(summary.get("reviewed_count") or 0)
    pending_count = int(summary.get("pending_count") or 0)
    within_sla_count = int(summary.get("reviewed_within_sla_count") or 0)
    stale_pending_count = int(summary.get("stale_pending_count") or 0)

    pending_rows = backend._edu_execute(
        """
        SELECT f.case_id, f.email, f.created_at, f.event_payload
        FROM edu_vp_training_event_log f
        WHERE f.event_type = 'safety_coach_feedback'
          AND f.event_name = 'answer_feedback_recorded'
          AND f.event_payload->>'rating' = 'down'
          AND f.created_at >= NOW() - (%s || ' days')::INTERVAL
          AND NOT EXISTS (
              SELECT 1
              FROM edu_vp_training_event_log r
              WHERE r.event_type = 'safety_coach_feedback'
                AND r.event_name = 'answer_auto_reinforcement_reviewed'
                AND r.case_id IS NOT DISTINCT FROM f.case_id
                AND r.email = f.email
                AND r.event_payload->>'question' = f.event_payload->>'question'
                AND r.event_payload->>'answer' = f.event_payload->>'answer'
                AND r.event_payload->>'feedback_saved_at' = f.event_payload->>'feedback_saved_at'
          )
        ORDER BY f.created_at ASC
        LIMIT %s
        """,
        (str(safe_days), safe_limit),
        fetch=True,
    )
    pending_samples: list[dict[str, Any]] = []
    for row in pending_rows or []:
        payload = row.get("event_payload") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        if not isinstance(payload, dict):
            payload = {}
        pending_samples.append(
            {
                "case_id": row.get("case_id"),
                "created_at": row.get("created_at"),
                "question": str(payload.get("question") or "")[:240],
                "answer_version": str(payload.get("answer_version") or "")[:80],
            }
        )

    reviewed_rate = reviewed_count / downvote_count if downvote_count else 1.0
    sla_rate = within_sla_count / reviewed_count if reviewed_count else 1.0
    ok = stale_pending_count == 0 and reviewed_rate >= 0.99
    return _json_safe(
        {
            "ok": ok,
            "lookback_days": safe_days,
            "sla_minutes": safe_sla,
            "downvote_count": downvote_count,
            "reviewed_count": reviewed_count,
            "pending_count": pending_count,
            "stale_pending_count": stale_pending_count,
            "reviewed_within_sla_count": within_sla_count,
            "review_completion_rate": round(reviewed_rate, 4),
            "review_sla_rate": round(sla_rate, 4),
            "last_downvote_at": summary.get("last_downvote_at"),
            "last_review_at": summary.get("last_review_at"),
            "pending_samples": pending_samples,
            "policy_candidates": _count_policy_candidates(),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Report EDU safety-coach downvote auto-reinforcement health.")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--sla-minutes", type=int, default=5)
    parser.add_argument("--pending-limit", type=int, default=10)
    args = parser.parse_args()
    report = run_report(lookback_days=args.lookback_days, sla_minutes=args.sla_minutes, pending_limit=args.pending_limit)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
