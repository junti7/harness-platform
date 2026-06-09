from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from core.database import execute_query
from scripts.llm_fallback_manager import load_recent_fallback_events
from scripts.summarize_conference_room_audit import _extract_persona_rows, _load_records as _load_conference_records
from scripts.summarize_openclaw_route_audit import (
    _load_records as _load_route_records,
    _response_records,
    _route_class,
    _route_records,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path("docs/reviews/weekly_ops_card")
DEFAULT_ROUTE_AUDIT_PATH = Path("runtime/openclaw_route_audit.jsonl")
DEFAULT_CONFERENCE_AUDIT_PATH = Path("docs/reports/conference_room_stream.jsonl")
INITIAL_OPS_BUDGET_USD = 7000.0
FIXED_SUBS_USD = 20.0 + 20.0 + 20.0 + 8.33


def _query_rows(query: str, params: tuple | None = None) -> list[dict[str, Any]]:
    rows = execute_query(query, params, fetch=True)
    return [dict(row) for row in (rows or [])]


def _latest_goal_forecast() -> dict[str, Any] | None:
    try:
        rows = _query_rows(
            """
            SELECT g.id, g.title, g.target_metric, g.target_value, g.unit,
                   s.actual_value, s.expected_value, s.health_status,
                   f.probability_to_hit, f.recommended_mode
            FROM strategic_goals g
            LEFT JOIN LATERAL (
                SELECT actual_value, expected_value, health_status
                FROM goal_progress_snapshots
                WHERE goal_id = g.id
                ORDER BY snapshot_date DESC, id DESC
                LIMIT 1
            ) s ON TRUE
            LEFT JOIN LATERAL (
                SELECT probability_to_hit, recommended_mode
                FROM goal_forecasts
                WHERE goal_id = g.id
                ORDER BY id DESC
                LIMIT 1
            ) f ON TRUE
            WHERE g.status NOT IN ('completed', 'cancelled', 'archived')
            ORDER BY g.updated_at DESC, g.id DESC
            LIMIT 1
            """
        )
        return rows[0] if rows else None
    except Exception:
        return None


def _ops_finance_snapshot() -> dict[str, Any]:
    try:
        rows = _query_rows(
            """
            SELECT 
                created_at::date AS day,
                provider,
                CASE provider
                    WHEN 'anthropic' THEN (input_tokens::float/1000000*3.0) + (output_tokens::float/1000000*15.0)
                    WHEN 'google'    THEN (input_tokens::float/1000000*3.5) + (output_tokens::float/1000000*10.5)
                    WHEN 'openai'    THEN (input_tokens::float/1000000*5.0) + (output_tokens::float/1000000*15.0)
                    ELSE 0
                END AS cost
            FROM api_cost_log
            WHERE created_at >= '2026-05-01'
            """
        )
    except Exception:
        return {
            "initial_budget_usd": INITIAL_OPS_BUDGET_USD,
            "total_spent_usd": 0.0,
            "remaining_budget_usd": INITIAL_OPS_BUDGET_USD,
            "avg_daily_burn_usd": 0.0,
            "runway_days": None,
        }
    total_api = sum(float(row.get("cost") or 0.0) for row in rows)
    total_spent = total_api + FIXED_SUBS_USD
    remaining_budget = max(0.0, INITIAL_OPS_BUDGET_USD - total_spent)

    last_30d_daily: dict[str, float] = {}
    for row in rows:
        day = str(row.get("day") or "")
        last_30d_daily[day] = last_30d_daily.get(day, 0.0) + float(row.get("cost") or 0.0)
    trailing_days = sorted(last_30d_daily.keys())[-30:]
    avg_daily_api_burn = (
        sum(last_30d_daily[day] for day in trailing_days) / len(trailing_days)
        if trailing_days else 0.0
    )
    avg_daily_total_burn = avg_daily_api_burn + (FIXED_SUBS_USD / 30.0)
    runway_days = (remaining_budget / avg_daily_total_burn) if avg_daily_total_burn > 0 else None
    return {
        "initial_budget_usd": INITIAL_OPS_BUDGET_USD,
        "total_spent_usd": total_spent,
        "remaining_budget_usd": remaining_budget,
        "avg_daily_burn_usd": avg_daily_total_burn,
        "runway_days": runway_days,
    }


def _build_ops_snapshot(route_records: list[dict[str, Any]], conference_records: list[dict[str, Any]]) -> dict[str, Any]:
    route_only = _route_records(route_records)
    response_only = _response_records(route_records)
    conference_rows = _extract_persona_rows(conference_records)
    incidents = load_recent_fallback_events(limit=50)

    route_classes = Counter(_route_class(str(record.get("route") or "")) for record in route_only)
    premium = route_classes.get("premium", 0)
    total_routes = len(route_only)
    premium_share = (premium / total_routes) if total_routes else 0.0
    avg_response_chars = (
        sum(int(r.get("response_chars") or 0) for r in response_only) / len(response_only)
        if response_only
        else None
    )

    noisy_messages = sum(1 for row in conference_rows if row["noise"])
    noisy_rate = (noisy_messages / len(conference_rows)) if conference_rows else 0.0
    avg_conference_chars = (
        sum(int(row["chars"]) for row in conference_rows) / len(conference_rows)
        if conference_rows
        else None
    )
    longest_persona = None
    if conference_rows:
        by_author: dict[str, list[int]] = {}
        for row in conference_rows:
            by_author.setdefault(str(row["author"]), []).append(int(row["chars"]))
        longest_persona = max(
            ((author, sum(values) / len(values)) for author, values in by_author.items()),
            key=lambda item: item[1],
        )

    incident_counts = Counter(str(item.get("event_type") or "unknown") for item in incidents)
    top_incident_persona = None
    if incidents:
        persona_counts = Counter(str(item.get("persona_display") or item.get("persona_handle") or "unknown") for item in incidents)
        top_incident_persona = persona_counts.most_common(1)[0]
    goal_forecast = _latest_goal_forecast()
    finance = _ops_finance_snapshot()

    return {
        "routes_total": total_routes,
        "premium_share": premium_share,
        "avg_response_chars": avg_response_chars,
        "conference_messages": len(conference_rows),
        "conference_noisy_rate": noisy_rate,
        "avg_conference_chars": avg_conference_chars,
        "longest_persona": longest_persona,
        "provider_incidents": incident_counts,
        "top_incident_persona": top_incident_persona,
        "goal_forecast": goal_forecast,
        "finance": finance,
    }


def _executive_verdict(snapshot: dict[str, Any]) -> tuple[str, str, str]:
    noisy_rate = float(snapshot.get("conference_noisy_rate") or 0.0)
    premium_share = float(snapshot.get("premium_share") or 0.0)
    incidents = int(sum((snapshot.get("provider_incidents") or {}).values()))
    avg_response_chars = float(snapshot.get("avg_response_chars") or 0.0)
    goal_forecast = snapshot.get("goal_forecast") or {}
    probability = goal_forecast.get("probability_to_hit")
    runway_days = (snapshot.get("finance") or {}).get("runway_days")

    health = "green"
    if noisy_rate >= 0.30 or premium_share >= 0.35 or incidents >= 6 or avg_response_chars >= 220 or (probability is not None and float(probability) < 0.6) or (runway_days is not None and float(runway_days) < 365):
        health = "yellow"
    if noisy_rate >= 0.45 or premium_share >= 0.50 or incidents >= 10 or avg_response_chars >= 320 or (probability is not None and float(probability) < 0.4) or (runway_days is not None and float(runway_days) < 180):
        health = "red"

    if probability is not None and float(probability) < 0.4:
        top_risk = "Goal hit probability remains below 40%."
        next_action = "Tighten the acquisition plan around the active goal and review the forecast mode before expanding surface area."
    elif runway_days is not None and float(runway_days) < 180:
        top_risk = "Ops budget runway has fallen below 180 days."
        next_action = "Lower premium routing and review fixed-cost assumptions before adding more automation scope."
    elif incidents >= max(3, int((snapshot.get("provider_incidents") or {}).get("fallback_activated", 0))):
        top_risk = "Provider fallback incidents remain elevated."
        next_action = "Keep Claude-dependent personas on Gemini fallback and verify recovery before re-enabling primary."
    elif noisy_rate >= 0.30:
        top_risk = "Conference-room chatter is still too noisy."
        next_action = "Trim the longest personas again and keep greeting/tool-noise filters active."
    elif premium_share >= 0.35:
        top_risk = "Premium routing is still too high for routine traffic."
        next_action = "Push more status/mail/risk queries onto deterministic or economy paths."
    else:
        top_risk = "Control-plane cost and chatter are within current operating guardrails."
        next_action = "Keep the current routing policy and watch next week deltas."

    return health, top_risk, next_action


def build_summary(route_records: list[dict[str, Any]], conference_records: list[dict[str, Any]], *, generated_for: str | None = None) -> str:
    generated_for = generated_for or date.today().isoformat()
    snapshot = _build_ops_snapshot(route_records, conference_records)
    health, top_risk, next_action = _executive_verdict(snapshot)
    longest_persona = snapshot.get("longest_persona")
    top_incident_persona = snapshot.get("top_incident_persona")
    incident_counts = snapshot.get("provider_incidents") or {}
    goal_forecast = snapshot.get("goal_forecast") or {}
    finance = snapshot.get("finance") or {}

    lines = [
        f"# CEO Weekly Ops Card - {generated_for}",
        "",
        "## Executive Summary",
        "",
        f"- health: {health}",
        f"- top_risk: {top_risk}",
        f"- next_action: {next_action}",
        "",
        "## Control Plane",
        "",
        f"- route_records: {snapshot['routes_total']}",
        f"- premium_share: {snapshot['premium_share']:.1%}",
        f"- avg_response_chars: {snapshot['avg_response_chars']:.1f}" if snapshot["avg_response_chars"] is not None else "- avg_response_chars: n/a",
        "",
        "## Goal Forecast",
        "",
        (
            f"- active_goal: {goal_forecast.get('title')} | p_hit={float(goal_forecast.get('probability_to_hit') or 0.0):.0%} | "
            f"health={goal_forecast.get('health_status') or '-'} | mode={goal_forecast.get('recommended_mode') or '-'}"
            if goal_forecast else "- active_goal: n/a"
        ),
        (
            f"- actual_vs_expected: {goal_forecast.get('actual_value')} / {goal_forecast.get('expected_value')}"
            if goal_forecast else "- actual_vs_expected: n/a"
        ),
        "",
        "## Conference Room",
        "",
        f"- messages: {snapshot['conference_messages']}",
        f"- noisy_rate: {snapshot['conference_noisy_rate']:.1%}",
        (
            f"- longest_persona: {longest_persona[0]} ({longest_persona[1]:.1f} chars)"
            if longest_persona else "- longest_persona: n/a"
        ),
        f"- avg_message_chars: {snapshot['avg_conference_chars']:.1f}" if snapshot["avg_conference_chars"] is not None else "- avg_message_chars: n/a",
        "",
        "## Provider Incidents",
        "",
        f"- fallback_activated: {incident_counts.get('fallback_activated', 0)}",
        f"- fallback_recovered: {incident_counts.get('fallback_recovered', 0)}",
        f"- fallback_cleared: {incident_counts.get('fallback_cleared', 0)}",
        (
            f"- top_incident_persona: {top_incident_persona[0]} ({top_incident_persona[1]})"
            if top_incident_persona else "- top_incident_persona: n/a"
        ),
        "",
        "## Finance",
        "",
        f"- ops_budget_spent_usd: {finance.get('total_spent_usd', 0.0):.2f}",
        f"- ops_budget_remaining_usd: {finance.get('remaining_budget_usd', 0.0):.2f}",
        f"- avg_daily_burn_usd: {finance.get('avg_daily_burn_usd', 0.0):.2f}",
        (
            f"- ops_runway_days: {finance.get('runway_days'):.0f}"
            if finance.get("runway_days") is not None else "- ops_runway_days: n/a"
        ),
    ]
    return "\n".join(lines) + "\n"


def _build_slack_summary(route_records: list[dict[str, Any]], conference_records: list[dict[str, Any]]) -> str:
    snapshot = _build_ops_snapshot(route_records, conference_records)
    health, top_risk, next_action = _executive_verdict(snapshot)
    incident_counts = snapshot.get("provider_incidents") or {}
    longest_persona = snapshot.get("longest_persona")
    longest_persona_text = f"{longest_persona[0]} {longest_persona[1]:.0f}" if longest_persona else "n/a"
    goal_forecast = snapshot.get("goal_forecast") or {}
    finance = snapshot.get("finance") or {}

    return "\n".join(
        [
            "CEO weekly ops card",
            f"- health: {health}",
            f"- top risk: {top_risk}",
            (
                f"- goal forecast: {float(goal_forecast.get('probability_to_hit') or 0.0):.0%} / {goal_forecast.get('recommended_mode') or '-'}"
                if goal_forecast else "- goal forecast: n/a"
            ),
            f"- route premium share: {snapshot['premium_share']:.1%}",
            (
                f"- route avg chars: {snapshot['avg_response_chars']:.1f}"
                if snapshot["avg_response_chars"] is not None else "- route avg chars: n/a"
            ),
            f"- conference noisy rate: {snapshot['conference_noisy_rate']:.1%}",
            f"- conference longest persona: {longest_persona_text}",
            (
                f"- ops runway: {finance.get('runway_days'):.0f}d"
                if finance.get("runway_days") is not None else "- ops runway: n/a"
            ),
            (
                f"- provider incidents: activated {incident_counts.get('fallback_activated', 0)} / "
                f"recovered {incident_counts.get('fallback_recovered', 0)} / "
                f"cleared {incident_counts.get('fallback_cleared', 0)}"
            ),
            f"- next action: {next_action}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a single CEO weekly ops card from route + conference audits.")
    parser.add_argument("--route-audit-path", type=Path, default=DEFAULT_ROUTE_AUDIT_PATH)
    parser.add_argument("--conference-audit-path", type=Path, default=DEFAULT_CONFERENCE_AUDIT_PATH)
    parser.add_argument("--route-limit", type=int, default=500)
    parser.add_argument("--conference-limit", type=int, default=500)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-name")
    parser.add_argument("--to-slack", action="store_true")
    parser.add_argument("--route", default="exec_president_decisions")
    args = parser.parse_args()

    route_records = _load_route_records(args.route_audit_path, limit=args.route_limit)
    conference_records = _load_conference_records(args.conference_audit_path, limit=args.conference_limit)
    summary = build_summary(route_records, conference_records, generated_for=args.date)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_name = args.output_name or f"ceo_weekly_ops_card_{args.date}.md"
    output_path = args.output_dir / output_name
    output_path.write_text(summary, encoding="utf-8")

    result: dict[str, Any] = {
        "route_records": len(route_records),
        "conference_records": len(conference_records),
        "output_path": str(output_path),
    }

    if args.to_slack:
        from adapters.content.slack_router import send_slack_route

        send_slack_route(args.route, {"text": _build_slack_summary(route_records, conference_records)})
        result["slack_route"] = args.route

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
