from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from typing import Any

from core.database import execute_query
from scripts.goal_loop import record_goal_snapshot
from scripts.goal_providers import registry as provider_registry


def _query_rows(query: str, params: tuple | None = None) -> list[dict[str, Any]]:
    rows = execute_query(query, params, fetch=True)
    return [dict(row) for row in (rows or [])]


def _active_goals() -> list[dict[str, Any]]:
    return _query_rows(
        """
        SELECT id, title, target_metric, target_value, current_value, baseline_value, unit,
               deadline, status, channel, metadata, created_at, updated_at
        FROM strategic_goals
        WHERE status NOT IN ('completed', 'cancelled', 'archived')
        ORDER BY updated_at DESC, id DESC
        """
    )


def _latest_subscriber_snapshot(platform: str) -> dict[str, Any]:
    rows = _query_rows(
        """
        SELECT snapshot_date, free_subscribers, paid_subscribers
        FROM subscriber_snapshots
        WHERE platform = %s
        ORDER BY snapshot_date DESC
        LIMIT 1
        """,
        (platform,),
    )
    return rows[0] if rows else {}


def _infer_provider(goal: dict[str, Any]) -> str | None:
    metadata = goal.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}
    provider = str(metadata.get("provider") or "").strip().lower()
    if provider:
        return provider
    channel = str(goal.get("channel") or "").strip().lower()
    if channel in {"substack", "maily"}:
        return channel
    target_metric = str(goal.get("target_metric") or "").strip().lower()
    if target_metric in {
        "free_subscribers",
        "paid_subscribers",
        "followers",
        "recommendation_subscribers",
        "direct_subscribers",
    }:
        return "substack"
    return None


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    for parser in (datetime.fromisoformat,):
        try:
            return parser(raw.replace("Z", "+00:00"))
        except Exception:
            continue
    return None


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pace_forecast(goal: dict[str, Any], actual_value: float, today: date | None = None) -> tuple[float | None, float | None, str, str]:
    today = today or date.today()
    created_at = _to_datetime(goal.get("created_at")) or datetime.combine(today, datetime.min.time())
    deadline = _to_datetime(goal.get("deadline"))
    baseline = float(goal.get("baseline_value") or 0.0)
    target = float(goal.get("target_value") or 0.0)
    unit = str(goal.get("unit") or "").strip()

    if deadline is None or deadline.date() <= created_at.date():
        return None, None, "yellow", "pace_model=unavailable"

    total_days = max((deadline.date() - created_at.date()).days, 1)
    elapsed_days = _clip((today - created_at.date()).days, 0, total_days)
    elapsed_ratio = elapsed_days / total_days

    expected_value = baseline + ((target - baseline) * elapsed_ratio)
    needed = target - baseline
    progressed = actual_value - baseline
    projected_final = actual_value if elapsed_ratio <= 0 else baseline + (progressed / elapsed_ratio)

    if elapsed_days <= 2:
        note = (
            f"pace_model=warmup created={created_at.date()} deadline={deadline.date()} "
            f"expected={expected_value:.2f}{unit and ' ' + unit} projected_final=unknown"
        )
        return round(expected_value, 2), 0.5, "green", note

    if needed <= 0:
        probability = 0.95
        health = "green"
    else:
        probability = _clip(projected_final / target if target > 0 else 0.5, 0.05, 0.95)
        if actual_value >= expected_value:
            health = "green"
        elif actual_value >= (baseline + ((target - baseline) * max(elapsed_ratio - 0.1, 0))):
            health = "yellow"
        else:
            health = "red"

    note = (
        f"pace_model=linear created={created_at.date()} deadline={deadline.date()} "
        f"expected={expected_value:.2f}{unit and ' ' + unit} projected_final={projected_final:.2f}"
    )
    return round(expected_value, 2), round(probability, 4), health, note


def _resolve_actual_value(goal: dict[str, Any], metrics: dict[str, Any], provider_name: str) -> float:
    target_metric = str(goal.get("target_metric") or "").strip()
    if target_metric and metrics.get(target_metric) is not None:
        return float(metrics[target_metric])
    return float(provider_registry.get(provider_name).primary_value(metrics))


def _hydrate_missing_metrics(provider_name: str, metrics: dict[str, Any]) -> dict[str, Any]:
    hydrated = dict(metrics)
    if provider_name not in {"substack", "maily"}:
        return hydrated
    latest = _latest_subscriber_snapshot(provider_name)
    for key in ("free_subscribers", "paid_subscribers"):
        if hydrated.get(key) is None and latest.get(key) is not None:
            hydrated[key] = latest[key]
    return hydrated


def record_active_goal_snapshots(today: date | None = None) -> list[dict[str, Any]]:
    goals = _active_goals()
    if not goals:
        return []

    provider_metrics: dict[str, dict[str, Any]] = {}
    recorded: list[dict[str, Any]] = []
    for goal in goals:
        provider_name = _infer_provider(goal)
        if not provider_name:
            continue
        if provider_name not in provider_metrics:
            raw_metrics = provider_registry.get(provider_name).fetch_metrics()
            provider_metrics[provider_name] = _hydrate_missing_metrics(provider_name, raw_metrics)
        metrics = provider_metrics[provider_name]
        actual_value = _resolve_actual_value(goal, metrics, provider_name)
        expected_value, probability, health_status, note = _pace_forecast(goal, actual_value, today=today)
        snapshot = record_goal_snapshot(
            goal_id=int(goal["id"]),
            actual_value=actual_value,
            expected_value=expected_value,
            forecast_probability=probability,
            health_status=health_status,
            notes=note,
            source_metrics_json=json.dumps(metrics, ensure_ascii=False),
            components_json=json.dumps(provider_registry.get(provider_name).build_components(metrics), ensure_ascii=False),
            snapshot_date=(today or date.today()).isoformat(),
        )
        recorded.append(dict(snapshot))
    return recorded


def main() -> None:
    parser = argparse.ArgumentParser(description="Record daily goal snapshots for active strategic goals.")
    parser.add_argument("--date", help="Snapshot date in YYYY-MM-DD format")
    args = parser.parse_args()
    snapshot_day = date.fromisoformat(args.date) if args.date else None
    snapshots = record_active_goal_snapshots(today=snapshot_day)
    print(json.dumps({"recorded": len(snapshots), "goal_ids": [s.get("goal_id") for s in snapshots]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
