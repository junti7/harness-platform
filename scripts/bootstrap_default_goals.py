from __future__ import annotations

import json
from datetime import date, timedelta

from core.database import execute_query
from scripts.goal_loop import create_goal, set_goal_model


def _query_rows(query: str, params: tuple | None = None) -> list[dict]:
    rows = execute_query(query, params, fetch=True)
    return [dict(row) for row in (rows or [])]


def _latest_substack_snapshot() -> dict:
    rows = _query_rows(
        """
        SELECT snapshot_date, free_subscribers, paid_subscribers
        FROM subscriber_snapshots
        WHERE platform = 'substack'
        ORDER BY snapshot_date DESC
        LIMIT 1
        """
    )
    return rows[0] if rows else {"free_subscribers": 0, "paid_subscribers": 0}


def _bootstrap_goal(*, title: str, objective: str, target_metric: str, target_value: float, current_value: float) -> int:
    created = create_goal(
        title=title,
        objective=objective,
        target_metric=target_metric,
        target_value=target_value,
        deadline=(date.today() + timedelta(days=30)).isoformat(),
        goal_type="growth",
        channel="substack",
        unit="subscribers",
        urgency="high",
        baseline_value=current_value,
        current_value=current_value,
        success_definition=f"{target_metric} reaches {target_value} within 30 days",
        failure_definition=f"{target_metric} misses {target_value} within 30 days",
        metadata_json=json.dumps({"provider": "substack", "bootstrap": "default_phase1"}, ensure_ascii=False),
    )
    goal_id = int(created["id"])
    execute_query("UPDATE strategic_goals SET status = 'active' WHERE id = %s", (goal_id,))
    set_goal_model(
        goal_id=goal_id,
        model_type="deterministic_linear_pace",
        objective_metric=target_metric,
        model_equation="expected_t = baseline + (target - baseline) * elapsed_ratio; projected_final = baseline + (actual - baseline) / elapsed_ratio",
        variable_definitions_json=json.dumps(
            {
                "baseline": "starting subscriber count",
                "target": "deadline subscriber target",
                "elapsed_ratio": "elapsed_days / total_days",
                "actual": "current subscriber count",
            },
            ensure_ascii=False,
        ),
        parameter_estimates_json=json.dumps({"cadence": "daily_snapshot"}, ensure_ascii=False),
        sensitivity_rank_json=json.dumps([target_metric, "elapsed_ratio"], ensure_ascii=False),
        trigger_thresholds_json=json.dumps(
            {"local_revision_probability_below": 0.7, "escalate_probability_below": 0.5},
            ensure_ascii=False,
        ),
        scenario_assumptions_json=json.dumps({"provider": "substack", "horizon_days": 30}, ensure_ascii=False),
    )
    return goal_id


def ensure_default_goals() -> list[int]:
    existing = _query_rows("SELECT id FROM strategic_goals ORDER BY id LIMIT 1")
    if existing:
        return []

    snapshot = _latest_substack_snapshot()
    free_now = float(snapshot.get("free_subscribers") or 0)
    paid_now = float(snapshot.get("paid_subscribers") or 0)
    created_ids = [
        _bootstrap_goal(
            title="30일 내 무료 구독자 50명 확보",
            objective="Phase 1에서 무료 구독자 50명을 달성해 익명 독자 유입 가설을 검증합니다.",
            target_metric="free_subscribers",
            target_value=max(50.0, free_now),
            current_value=free_now,
        ),
        _bootstrap_goal(
            title="30일 내 paid subscriber 1명 확보",
            objective="Phase 1에서 첫 paid subscriber 1명을 확보해 유료 전환 가설을 검증합니다.",
            target_metric="paid_subscribers",
            target_value=max(1.0, paid_now),
            current_value=paid_now,
        ),
    ]
    return created_ids


def main() -> None:
    goal_ids = ensure_default_goals()
    print(json.dumps({"created_goal_ids": goal_ids}, ensure_ascii=False))


if __name__ == "__main__":
    main()
