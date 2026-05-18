import json
import uuid
from typing import Any

from core.database import execute_query


def _new_cid() -> str:
    return str(uuid.uuid4())


def _first_row(rows: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not rows:
        raise ValueError("query returned no rows")
    return dict(rows[0])


def _parse_json_arg(value: str | None, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    raw = value.strip()
    if not raw:
        return default
    return json.loads(raw)


def create_goal(
    *,
    title: str,
    objective: str,
    target_metric: str,
    target_value: float,
    deadline: str,
    goal_type: str = "growth",
    channel: str | None = None,
    unit: str = "count",
    urgency: str = "medium",
    baseline_value: float = 0.0,
    current_value: float = 0.0,
    success_definition: str | None = None,
    failure_definition: str | None = None,
    constraints_json: str | None = None,
    metadata_json: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    row = _first_row(
        execute_query(
            """
            INSERT INTO strategic_goals (
                title,
                objective,
                goal_type,
                channel,
                target_metric,
                target_value,
                current_value,
                baseline_value,
                unit,
                deadline,
                status,
                urgency,
                owner_team,
                success_definition,
                failure_definition,
                constraints_json,
                metadata,
                correlation_id
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                'draft', %s, 'Business Operations Team', %s, %s, %s::jsonb, %s::jsonb, %s::uuid
            )
            RETURNING *
            """,
            (
                title,
                objective,
                goal_type,
                channel,
                target_metric,
                target_value,
                current_value,
                baseline_value,
                unit,
                deadline,
                urgency,
                success_definition,
                failure_definition,
                json.dumps(_parse_json_arg(constraints_json, {}), ensure_ascii=False),
                json.dumps(_parse_json_arg(metadata_json, {}), ensure_ascii=False),
                correlation_id or _new_cid(),
            ),
            fetch=True,
        )
    )
    return row


def set_goal_model(
    *,
    goal_id: int,
    model_type: str,
    objective_metric: str,
    model_equation: str,
    variable_definitions_json: str | None = None,
    parameter_estimates_json: str | None = None,
    sensitivity_rank_json: str | None = None,
    trigger_thresholds_json: str | None = None,
    scenario_assumptions_json: str | None = None,
    created_by: str = "Business Operations Team",
    activate: bool = True,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    current = execute_query(
        "SELECT COALESCE(MAX(version), 0) AS version FROM goal_model_specs WHERE goal_id = %s",
        (goal_id,),
        fetch=True,
    )
    next_version = int(_first_row(current)["version"]) + 1

    if activate:
        execute_query(
            "UPDATE goal_model_specs SET active = FALSE, updated_at = NOW() WHERE goal_id = %s AND active = TRUE",
            (goal_id,),
        )

    row = _first_row(
        execute_query(
            """
            INSERT INTO goal_model_specs (
                goal_id,
                version,
                model_type,
                objective_metric,
                model_equation,
                variable_definitions,
                parameter_estimates,
                sensitivity_rank,
                trigger_thresholds,
                scenario_assumptions,
                active,
                created_by,
                correlation_id
            )
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s::uuid)
            RETURNING *
            """,
            (
                goal_id,
                next_version,
                model_type,
                objective_metric,
                model_equation,
                json.dumps(_parse_json_arg(variable_definitions_json, {}), ensure_ascii=False),
                json.dumps(_parse_json_arg(parameter_estimates_json, {}), ensure_ascii=False),
                json.dumps(_parse_json_arg(sensitivity_rank_json, []), ensure_ascii=False),
                json.dumps(_parse_json_arg(trigger_thresholds_json, {}), ensure_ascii=False),
                json.dumps(_parse_json_arg(scenario_assumptions_json, {}), ensure_ascii=False),
                activate,
                created_by,
                correlation_id or _new_cid(),
            ),
            fetch=True,
        )
    )
    return row


def _active_model(goal_id: int) -> dict[str, Any] | None:
    rows = execute_query(
        """
        SELECT *
        FROM goal_model_specs
        WHERE goal_id = %s AND active = TRUE
        ORDER BY version DESC
        LIMIT 1
        """,
        (goal_id,),
        fetch=True,
    )
    return dict(rows[0]) if rows else None


def record_goal_snapshot(
    *,
    goal_id: int,
    actual_value: float,
    expected_value: float | None = None,
    forecast_probability: float | None = None,
    health_status: str = "green",
    notes: str | None = None,
    source_metrics_json: str | None = None,
    snapshot_date: str | None = None,
    components_json: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    model = _active_model(goal_id)
    model_spec_id = model["id"] if model else None
    variance = None
    if expected_value is not None:
        variance = actual_value - expected_value

    row = _first_row(
        execute_query(
            """
            INSERT INTO goal_progress_snapshots (
                goal_id,
                model_spec_id,
                snapshot_date,
                actual_value,
                expected_value,
                forecast_probability,
                variance,
                health_status,
                notes,
                source_metrics_json,
                correlation_id
            )
            VALUES (
                %s,
                %s,
                COALESCE(%s::date, CURRENT_DATE),
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s::jsonb,
                %s::uuid
            )
            RETURNING *
            """,
            (
                goal_id,
                model_spec_id,
                snapshot_date,
                actual_value,
                expected_value,
                forecast_probability,
                variance,
                health_status,
                notes,
                json.dumps(_parse_json_arg(source_metrics_json, {}), ensure_ascii=False),
                correlation_id or _new_cid(),
            ),
            fetch=True,
        )
    )

    execute_query(
        """
        UPDATE strategic_goals
        SET current_value = %s,
            updated_at = NOW()
        WHERE id = %s
        """,
        (actual_value, goal_id),
    )

    components = _parse_json_arg(components_json, [])
    if model_spec_id and components:
        for component in components:
            name = component["component_name"]
            expected = component.get("expected_value")
            actual = component.get("actual_value")
            comp_variance = component.get("variance")
            if comp_variance is None and expected is not None and actual is not None:
                comp_variance = actual - expected
            existing = execute_query(
                """
                SELECT id
                FROM goal_metric_components
                WHERE goal_id = %s AND model_spec_id = %s AND component_name = %s
                LIMIT 1
                """,
                (goal_id, model_spec_id, name),
                fetch=True,
            )
            if existing:
                execute_query(
                    """
                    UPDATE goal_metric_components
                    SET component_role = %s,
                        equation_term = %s,
                        expected_value = %s,
                        actual_value = %s,
                        variance = %s,
                        unit = %s,
                        source_metric_key = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        component.get("component_role", "driver"),
                        component.get("equation_term"),
                        expected,
                        actual,
                        comp_variance,
                        component.get("unit"),
                        component.get("source_metric_key"),
                        existing[0]["id"],
                    ),
                )
            else:
                execute_query(
                    """
                    INSERT INTO goal_metric_components (
                        goal_id,
                        model_spec_id,
                        component_name,
                        component_role,
                        equation_term,
                        expected_value,
                        actual_value,
                        variance,
                        unit,
                        source_metric_key
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        goal_id,
                        model_spec_id,
                        name,
                        component.get("component_role", "driver"),
                        component.get("equation_term"),
                        expected,
                        actual,
                        comp_variance,
                        component.get("unit"),
                        component.get("source_metric_key"),
                    ),
                )

    if model_spec_id and forecast_probability is not None:
        thresholds = model.get("trigger_thresholds") or {}
        mode = "stay_course"
        if forecast_probability < float(thresholds.get("escalate_probability_below", 0.4)):
            mode = "escalate"
        elif forecast_probability < float(thresholds.get("local_revision_probability_below", 0.7)):
            mode = "local_revision"
        execute_query(
            """
            INSERT INTO goal_forecasts (
                goal_id,
                model_spec_id,
                forecast_date,
                expected_deadline_value,
                probability_to_hit,
                confidence,
                narrative,
                recommended_mode
            )
            VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s, %s)
            """,
            (
                goal_id,
                model_spec_id,
                expected_value,
                forecast_probability,
                0.7,
                notes,
                mode,
            ),
        )

        if health_status in {"yellow", "red"} or mode != "stay_course":
            execute_query(
                """
                INSERT INTO goal_anomaly_events (
                    goal_id,
                    model_spec_id,
                    snapshot_id,
                    anomaly_type,
                    severity,
                    trigger_rule,
                    observed_value,
                    expected_value,
                    local_revision_recommended,
                    executive_escalation_required
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    goal_id,
                    model_spec_id,
                    row["id"],
                    "forecast_shortfall" if mode != "stay_course" else "health_degraded",
                    "high" if mode == "escalate" or health_status == "red" else "medium",
                    f"health={health_status}, probability_to_hit={forecast_probability}",
                    str(actual_value),
                    str(expected_value) if expected_value is not None else None,
                    mode != "stay_course" or health_status != "green",
                    mode == "escalate",
                ),
            )

    return row


def record_substack_goal_snapshot(
    *,
    goal_id: int,
    actual_value: float | None,
    expected_value: float | None = None,
    forecast_probability: float | None = None,
    health_status: str = "green",
    notes: str | None = None,
    snapshot_date: str | None = None,
    metrics: dict[str, Any] | None = None,
    follower_count: int | None = None,
    recommendation_subscribers: int | None = None,
    direct_subscribers: int | None = None,
    welcome_page_visitors: int | None = None,
    welcome_page_conversion_rate: float | None = None,
    note_publish_count: int | None = None,
) -> dict[str, Any]:
    payload = dict(metrics or {})
    if follower_count is not None:
        payload["followers"] = follower_count
    if recommendation_subscribers is not None:
        payload["recommendation_subscribers"] = recommendation_subscribers
    if direct_subscribers is not None:
        payload["direct_subscribers"] = direct_subscribers
    if welcome_page_visitors is not None:
        payload["welcome_page_visitors"] = welcome_page_visitors
    if welcome_page_conversion_rate is not None:
        payload["welcome_page_conversion_rate"] = welcome_page_conversion_rate
    if note_publish_count is not None:
        payload["note_publish_count"] = note_publish_count

    resolved_actual = actual_value
    if resolved_actual is None:
        resolved_actual = payload.get("free_subscribers")
    if resolved_actual is None:
        raise ValueError("actual_value 또는 metrics.free_subscribers 중 하나는 필요합니다.")

    components: list[dict[str, Any]] = []
    if "followers" in payload:
        components.append(
            {
                "component_name": "followers",
                "component_role": "upstream_audience",
                "actual_value": payload["followers"],
                "source_metric_key": "followers",
            }
        )
    if "welcome_page_visitors" in payload:
        components.append(
            {
                "component_name": "welcome_page_visitors",
                "component_role": "acquisition_input",
                "actual_value": payload["welcome_page_visitors"],
                "source_metric_key": "welcome_page_visitors",
            }
        )
    if "welcome_page_conversion_rate" in payload:
        components.append(
            {
                "component_name": "welcome_page_conversion_rate",
                "component_role": "conversion_rate",
                "actual_value": payload["welcome_page_conversion_rate"],
                "source_metric_key": "welcome_page_conversion_rate",
            }
        )
    if "recommendation_subscribers" in payload:
        components.append(
            {
                "component_name": "recommendation_subscribers",
                "component_role": "channel_output",
                "actual_value": payload["recommendation_subscribers"],
                "source_metric_key": "recommendation_subscribers",
            }
        )
    if "direct_subscribers" in payload:
        components.append(
            {
                "component_name": "direct_subscribers",
                "component_role": "channel_output",
                "actual_value": payload["direct_subscribers"],
                "source_metric_key": "direct_subscribers",
            }
        )
    if "note_publish_count" in payload:
        components.append(
            {
                "component_name": "note_publish_count",
                "component_role": "activity_driver",
                "actual_value": payload["note_publish_count"],
                "source_metric_key": "note_publish_count",
            }
        )

    return record_goal_snapshot(
        goal_id=goal_id,
        actual_value=float(resolved_actual),
        expected_value=expected_value,
        forecast_probability=forecast_probability,
        health_status=health_status,
        notes=notes,
        source_metrics_json=json.dumps(payload, ensure_ascii=False),
        snapshot_date=snapshot_date,
        components_json=json.dumps(components, ensure_ascii=False),
    )


def get_goal_model(goal_id: int) -> dict[str, Any]:
    rows = execute_query(
        """
        SELECT *
        FROM goal_model_specs
        WHERE goal_id = %s
        ORDER BY active DESC, version DESC
        LIMIT 1
        """,
        (goal_id,),
        fetch=True,
    )
    if not rows:
        raise ValueError(f"goal {goal_id} has no model spec")
    return dict(rows[0])


def get_goal_status(goal_id: int) -> dict[str, Any]:
    goal = _first_row(
        execute_query("SELECT * FROM strategic_goals WHERE id = %s", (goal_id,), fetch=True)
    )
    model = _active_model(goal_id)
    latest_snapshot = execute_query(
        """
        SELECT *
        FROM goal_progress_snapshots
        WHERE goal_id = %s
        ORDER BY snapshot_date DESC, created_at DESC
        LIMIT 1
        """,
        (goal_id,),
        fetch=True,
    )
    latest_forecast = execute_query(
        """
        SELECT *
        FROM goal_forecasts
        WHERE goal_id = %s
        ORDER BY forecast_date DESC, created_at DESC
        LIMIT 1
        """,
        (goal_id,),
        fetch=True,
    )
    latest_diagnostic = execute_query(
        """
        SELECT d.*, c.component_name
        FROM goal_diagnostic_events d
        LEFT JOIN goal_metric_components c ON c.id = d.primary_component_id
        WHERE d.goal_id = %s
        ORDER BY d.created_at DESC
        LIMIT 1
        """,
        (goal_id,),
        fetch=True,
    )
    anomaly_count = execute_query(
        """
        SELECT COUNT(*) AS unresolved_count
        FROM goal_anomaly_events
        WHERE goal_id = %s AND resolved = FALSE
        """,
        (goal_id,),
        fetch=True,
    )
    return {
        "goal": goal,
        "active_model": model,
        "latest_snapshot": dict(latest_snapshot[0]) if latest_snapshot else None,
        "latest_forecast": dict(latest_forecast[0]) if latest_forecast else None,
        "latest_diagnostic": dict(latest_diagnostic[0]) if latest_diagnostic else None,
        "unresolved_anomalies": int(_first_row(anomaly_count)["unresolved_count"]),
    }


def diagnose_goal(goal_id: int) -> dict[str, Any]:
    goal_status = get_goal_status(goal_id)
    model = goal_status["active_model"]
    snapshot = goal_status["latest_snapshot"]
    if not snapshot:
        raise ValueError(f"goal {goal_id} has no snapshot to diagnose")

    model_spec_id = model["id"] if model else None
    components = execute_query(
        """
        SELECT *
        FROM goal_metric_components
        WHERE goal_id = %s AND (%s IS NULL OR model_spec_id = %s)
        ORDER BY variance ASC NULLS LAST, updated_at DESC
        """,
        (goal_id, model_spec_id, model_spec_id),
        fetch=True,
    )

    primary_component = dict(components[0]) if components else None
    feedback_rows = execute_query(
        """
        SELECT source_type, signal_type, signal_text, severity
        FROM goal_feedback_signals
        WHERE goal_id = %s
        ORDER BY created_at DESC
        LIMIT 3
        """,
        (goal_id,),
        fetch=True,
    )
    feedback = [dict(row) for row in feedback_rows]

    forecast = goal_status["latest_forecast"] or {}
    probability = forecast.get("probability_to_hit")
    thresholds = (model or {}).get("trigger_thresholds") or {}
    escalate_cutoff = float(thresholds.get("escalate_probability_below", 0.4))
    executive_escalation_required = (
        snapshot.get("health_status") == "red"
        or (probability is not None and float(probability) < escalate_cutoff)
    )

    if primary_component:
        root_cause_hypothesis = (
            f"`{primary_component['component_name']}` 성분이 계획 대비 가장 크게 미달했습니다. "
            f"expected={primary_component.get('expected_value')}, actual={primary_component.get('actual_value')}, "
            f"variance={primary_component.get('variance')}."
        )
        diagnosis_type = "component_underperformance"
        primary_component_id = primary_component["id"]
    else:
        root_cause_hypothesis = (
            f"목표 전체 수준에서 shortfall이 감지되었습니다. "
            f"expected={snapshot.get('expected_value')}, actual={snapshot.get('actual_value')}, variance={snapshot.get('variance')}."
        )
        diagnosis_type = "goal_level_shortfall"
        primary_component_id = None

    if feedback:
        root_cause_hypothesis += " 최근 피드백 신호: " + "; ".join(
            f"{item['source_type']}:{item['signal_type']}={item['signal_text']}" for item in feedback
        )

    evidence = {
        "snapshot": {
            "actual_value": snapshot.get("actual_value"),
            "expected_value": snapshot.get("expected_value"),
            "variance": snapshot.get("variance"),
            "health_status": snapshot.get("health_status"),
        },
        "forecast_probability": probability,
        "primary_component": primary_component,
        "feedback_signals": feedback,
    }

    row = _first_row(
        execute_query(
            """
            INSERT INTO goal_diagnostic_events (
                goal_id,
                model_spec_id,
                snapshot_id,
                primary_component_id,
                diagnosis_type,
                root_cause_hypothesis,
                evidence_json,
                confidence,
                executive_escalation_required
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING *
            """,
            (
                goal_id,
                model_spec_id,
                snapshot["id"],
                primary_component_id,
                diagnosis_type,
                root_cause_hypothesis,
                json.dumps(evidence, ensure_ascii=False, default=str),
                0.75 if primary_component else 0.55,
                executive_escalation_required,
            ),
            fetch=True,
        )
    )
    row["diagnosis_type"] = diagnosis_type
    row["root_cause_hypothesis"] = root_cause_hypothesis
    row["executive_escalation_required"] = executive_escalation_required
    row["primary_component"] = primary_component
    row["feedback_signals"] = feedback
    return row
