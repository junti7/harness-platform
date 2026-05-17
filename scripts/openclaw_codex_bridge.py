import argparse
import json
import os
import shutil
import socket
import sys
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, ".")

from adapters.content.decision_card import build_decision_card, card_to_json, render_mobile_text
from adapters.content.mobile_dispatcher import build_slack_payload
from adapters.content.slack_router import route_label, send_slack_route
from core.approval import APPROVAL_TARGET_TYPES, VALID_APPROVAL_TYPES, VALID_DECISIONS
from scripts.ceo_decision import record_decision
from scripts.dispatch_llm_task_packet import build_packet, dispatch_packet
from scripts.goal_loop import (
    create_goal,
    diagnose_goal,
    get_goal_model,
    get_goal_status,
    record_goal_snapshot,
    record_substack_goal_snapshot,
    set_goal_model,
)
from scripts.goal_providers import registry as _provider_registry
from scripts.openclaw_ops_sync import publish_ops_brief
from scripts.system_integrity_check import run_check as run_system_integrity_check


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _detect_cli(command: str) -> dict[str, Any]:
    path = shutil.which(command)
    if not path:
        candidate = Path("/opt/homebrew/bin") / command
        if candidate.exists():
            path = str(candidate)
    return {"available": bool(path), "path": path}


def _detect_copilot() -> dict[str, Any]:
    candidate = "/opt/homebrew/bin/copilot"
    if Path(candidate).exists():
        return {"available": True, "path": candidate}
    return _detect_cli("copilot")


def _can_connect_db() -> tuple[bool, str | None]:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return False, "DATABASE_URL missing"
    try:
        from core.database import get_connection

        conn = get_connection()
        conn.close()
        return True, None
    except Exception as exc:
        return False, str(exc)


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def status_snapshot() -> dict[str, Any]:
    db_ok, db_error = _can_connect_db()
    integrity = run_system_integrity_check()
    return {
        "generated_at": _now(),
        "openclaw_bridge": "ready",
        "runtime": {
            "python": sys.executable,
            "cwd": os.getcwd(),
            "slack_phase": os.getenv("SLACK_PHASE", "phase1"),
            "slack_delivery_mode": os.getenv("SLACK_DELIVERY_MODE", "webhook"),
            "capital_actions_enabled": os.getenv("CAPITAL_ACTIONS_ENABLED", "false"),
        },
        "integrations": {
            "codex": {"available": True, "path": "current_session"},
            "openclaw": _detect_cli("openclaw"),
            "claude": _detect_cli("claude"),
            "gemini": _detect_cli("gemini"),
            "copilot": _detect_copilot(),
            "ollama": _detect_cli("ollama"),
            "postgres": {"available": db_ok, "error": db_error},
            "slack_bot": {"available": bool(os.getenv("SLACK_BOT_TOKEN"))},
            "slack_webhook": {"available": bool(os.getenv("SLACK_WEBHOOK_URL"))},
            "notion": {"available": bool(os.getenv("NOTION_API_KEY"))},
        },
        "services": {
            "ollama_11434": _port_open("127.0.0.1", 11434),
        },
        "integrity": integrity,
        "routes": {
            "openclaw_ops": route_label("agent_openclaw_routing"),
            "executive": route_label("exec_president_decisions"),
            "incidents": route_label("ops_incidents"),
        },
        "supported_commands": [
            "status",
            "decision-card",
            "record-decision",
            "goal-create",
            "goal-model",
            "goal-snapshot",
            "goal-substack-snapshot",
            "goal-provider-snapshot",
            "goal-diagnose",
            "goal-status",
            "route-note",
            "task-packet",
            "publish-ops-brief",
            "push-approval-card",
            "dispatch-task-packet",
            "run-pipeline",
        ],
    }


def _write_output(output: str, output_path: str | None) -> None:
    if not output_path:
        print(output)
        return

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")
    print(str(path))


def _json_dump(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str)


def command_status(args: argparse.Namespace) -> None:
    payload = status_snapshot()
    rendered = _json_dump(payload) if args.format == "json" else _render_status_text(payload)
    _write_output(rendered, args.output)


def _render_status_text(payload: dict[str, Any]) -> str:
    integrations = payload["integrations"]
    lines = [
        f"OpenClaw bridge: {payload['openclaw_bridge']}",
        f"Generated at: {payload['generated_at']}",
        f"Slack phase: {payload['runtime']['slack_phase']}",
        f"OpenClaw CLI: {integrations['openclaw']['available']}",
        f"Claude CLI: {integrations['claude']['available']}",
        f"Gemini CLI: {integrations['gemini']['available']}",
        f"Copilot CLI: {integrations['copilot']['available']}",
        f"Ollama CLI: {integrations['ollama']['available']}",
        f"Postgres: {integrations['postgres']['available']}",
        f"Slack bot token: {integrations['slack_bot']['available']}",
        f"Notion API: {integrations['notion']['available']}",
        f"OpenClaw route: {payload['routes']['openclaw_ops']}",
    ]
    if integrations["postgres"]["error"]:
        lines.append(f"Postgres error: {integrations['postgres']['error']}")
    integrity = payload.get("integrity") or {}
    lines.append(f"Integrity preflight: {integrity.get('ok', False)}")
    if integrity.get("findings"):
        lines.append(f"Integrity findings: {', '.join(integrity['findings'][:3])}")
    return "\n".join(lines)


def command_decision_card(args: argparse.Namespace) -> None:
    card = build_decision_card(args.target_type, args.target_id)
    if args.format == "json":
        rendered = card_to_json(card)
    elif args.format == "text":
        rendered = render_mobile_text(card)
    elif args.format == "slack-json":
        rendered = _json_dump(build_slack_payload(card))
    else:
        raise ValueError(f"Unsupported format: {args.format}")
    _write_output(rendered, args.output)


def command_record_decision(args: argparse.Namespace) -> None:
    record_decision(
        target_type=args.target_type,
        target_id=args.target_id,
        decision=args.decision,
        approval_type=args.approval_type,
        reason=args.reason,
    )
    payload = {
        "generated_at": _now(),
        "target_type": args.target_type,
        "target_id": args.target_id,
        "decision": args.decision,
        "approval_type": args.approval_type,
        "reason": args.reason,
    }
    _write_output(_json_dump(payload), args.output)


def command_route_note(args: argparse.Namespace) -> None:
    send_slack_route(
        args.route,
        {
            "text": args.text,
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": args.text},
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"source=OpenClaw bridge | generated_at={_now()}"}
                    ],
                },
            ],
        },
    )
    _write_output(
        _json_dump({"sent": True, "route": args.route, "channel": route_label(args.route), "text": args.text}),
        args.output,
    )


def command_task_packet(args: argparse.Namespace) -> None:
    packet = {
        "generated_at": _now(),
        "owner": "Codex Chief of Staff",
        "executor": args.executor,
        "task_kind": args.task_kind,
        "title": args.title,
        "objective": args.objective,
        "input_artifacts": args.input_artifact or [],
        "output_artifacts": args.output_artifact or [],
        "checks": args.check or [],
        "notes": args.note or [],
        "handoff": {
            "slack_route": args.route,
            "route_channel": route_label(args.route) if args.route else None,
            "callback_command": args.callback_command,
        },
    }
    _write_output(_json_dump(packet), args.output)


def command_publish_ops_brief(args: argparse.Namespace) -> None:
    result = publish_ops_brief(
        route=args.route,
        to_slack=args.to_slack,
        to_notion=args.to_notion,
        summary_text=args.summary_text,
        review_type=args.review_type,
    )
    _write_output(_json_dump(result), args.output)


def command_push_approval_card(args: argparse.Namespace) -> None:
    card = build_decision_card(args.target_type, args.target_id)
    payload = build_slack_payload(card)
    send_slack_route(args.route, payload)
    _write_output(
        _json_dump(
            {
                "sent": True,
                "route": args.route,
                "channel": route_label(args.route),
                "target_type": args.target_type,
                "target_id": args.target_id,
            }
        ),
        args.output,
    )


def command_dispatch_task_packet(args: argparse.Namespace) -> None:
    packet = build_packet(args)
    result = dispatch_packet(
        packet=packet,
        providers=args.provider or ["claude", "gemini", "copilot"],
        output_dir=Path(args.output_dir),
        notify_route=args.notify_route,
    )
    _write_output(_json_dump(result), args.output)


def command_run_pipeline(args: argparse.Namespace) -> None:
    from run_pipeline import run

    if args.notify_slack:
        send_slack_route(
            "agent_openclaw_routing",
            {"text": f"OpenClaw bridge requested pipeline run at {_now()}"},
        )
    run()
    result = {"generated_at": _now(), "executed": "run_pipeline.py", "notified_slack": args.notify_slack}
    _write_output(_json_dump(result), args.output)


def command_goal_create(args: argparse.Namespace) -> None:
    goal = create_goal(
        title=args.title,
        objective=args.objective,
        target_metric=args.target_metric,
        target_value=args.target_value,
        deadline=args.deadline,
        goal_type=args.goal_type,
        channel=args.channel,
        unit=args.unit,
        urgency=args.urgency,
        baseline_value=args.baseline_value,
        current_value=args.current_value,
        success_definition=args.success_definition,
        failure_definition=args.failure_definition,
        constraints_json=args.constraints_json,
        metadata_json=args.metadata_json,
    )
    _write_output(
        _json_dump(
            {
                "generated_at": _now(),
                "goal_id": goal["id"],
                "status": goal["status"],
                "title": goal["title"],
                "target_metric": goal["target_metric"],
                "target_value": goal["target_value"],
                "deadline": goal["deadline"],
            }
        ),
        args.output,
    )


def command_goal_model(args: argparse.Namespace) -> None:
    if args.equation:
        if not args.objective_metric:
            raise ValueError("--objective-metric is required when registering a goal model")
        model = set_goal_model(
            goal_id=args.goal_id,
            model_type=args.model_type,
            objective_metric=args.objective_metric,
            model_equation=args.equation,
            variable_definitions_json=args.variables_json,
            parameter_estimates_json=args.parameters_json,
            sensitivity_rank_json=args.sensitivity_json,
            trigger_thresholds_json=args.thresholds_json,
            scenario_assumptions_json=args.assumptions_json,
            created_by=args.created_by,
            activate=not args.inactive,
        )
    else:
        model = get_goal_model(args.goal_id)

    rendered = _json_dump(model) if args.format == "json" else _render_goal_model_text(model)
    _write_output(rendered, args.output)


def command_goal_snapshot(args: argparse.Namespace) -> None:
    snapshot = record_goal_snapshot(
        goal_id=args.goal_id,
        actual_value=args.actual_value,
        expected_value=args.expected_value,
        forecast_probability=args.forecast_probability,
        health_status=args.health_status,
        notes=args.notes,
        source_metrics_json=args.source_metrics_json,
        snapshot_date=args.snapshot_date,
        components_json=args.components_json,
    )
    _write_output(_json_dump(snapshot), args.output)


def command_goal_substack_snapshot(args: argparse.Namespace) -> None:
    metrics = fetch_subscriber_metrics()
    if args.free_subscribers is not None:
        metrics["free_subscribers"] = args.free_subscribers
    if args.paid_subscribers is not None:
        metrics["paid_subscribers"] = args.paid_subscribers
    if args.post_count is not None:
        metrics["post_count"] = args.post_count
    if args.draft_count is not None:
        metrics["draft_count"] = args.draft_count

    snapshot = record_substack_goal_snapshot(
        goal_id=args.goal_id,
        actual_value=args.actual_value,
        expected_value=args.expected_value,
        forecast_probability=args.forecast_probability,
        health_status=args.health_status,
        notes=args.notes or metrics.get("notes"),
        snapshot_date=args.snapshot_date,
        metrics=metrics,
        follower_count=args.followers,
        recommendation_subscribers=args.recommendation_subscribers,
        direct_subscribers=args.direct_subscribers,
        welcome_page_visitors=args.welcome_page_visitors,
        welcome_page_conversion_rate=args.welcome_page_conversion_rate,
        note_publish_count=args.note_publish_count,
    )
    _write_output(_json_dump(snapshot), args.output)


def command_goal_provider_snapshot(args: argparse.Namespace) -> None:
    import json as _json
    provider_name = args.provider.lower()
    adapter = _provider_registry.get(provider_name)  # raises ValueError for unknown providers

    metrics = adapter.fetch_metrics()

    # CLI overrides take precedence over fetched metrics
    override_keys = [
        "free_subscribers", "paid_subscribers", "post_count", "draft_count",
        "followers", "recommendation_subscribers", "direct_subscribers",
        "welcome_page_visitors", "welcome_page_conversion_rate", "note_publish_count",
    ]
    for key in override_keys:
        val = getattr(args, key, None)
        if val is not None:
            metrics[key] = val

    actual = args.actual_value if args.actual_value is not None else adapter.primary_value(metrics)
    components = adapter.build_components(metrics)

    snapshot = record_goal_snapshot(
        goal_id=args.goal_id,
        actual_value=float(actual),
        expected_value=args.expected_value,
        forecast_probability=args.forecast_probability,
        health_status=args.health_status,
        notes=args.notes or metrics.get("notes"),
        source_metrics_json=_json.dumps(metrics, ensure_ascii=False),
        snapshot_date=args.snapshot_date,
        components_json=_json.dumps(components, ensure_ascii=False),
    )
    _write_output(_json_dump(snapshot), args.output)


def command_goal_diagnose(args: argparse.Namespace) -> None:
    diagnosis = diagnose_goal(args.goal_id)
    rendered = _json_dump(diagnosis) if args.format == "json" else _render_goal_diagnosis_text(diagnosis)
    _write_output(rendered, args.output)


def command_goal_status(args: argparse.Namespace) -> None:
    if args.goal_id is None:
        # ID 없이 호출 → 전체 goal 목록 조회
        try:
            from core.database import get_connection
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id, title, target_metric, target_value, deadline, status "
                        "FROM strategic_goals ORDER BY id"
                    )
                    rows = cur.fetchall()
            if not rows:
                _write_output("등록된 goal이 없습니다.", args.output)
                return
            if args.format == "json":
                _write_output(_json_dump(rows), args.output)
            else:
                lines = [f"전체 Goal 목록 ({len(rows)}개):"]
                for r in rows:
                    deadline = str(r.get("deadline", ""))[:10] if r.get("deadline") else "기한 없음"
                    lines.append(
                        f"  #{r['id']} [{r.get('status', '?')}] {r['title']} "
                        f"| 지표: {r.get('target_metric', '?')} → {r.get('target_value', '?')} "
                        f"| 기한: {deadline}"
                    )
                _write_output("\n".join(lines), args.output)
        except Exception as exc:
            _write_output(f"❌ goal 목록 조회 실패: {exc}", args.output)
        return
    payload = get_goal_status(args.goal_id)
    rendered = _json_dump(payload) if args.format == "json" else _render_goal_status_text(payload)
    _write_output(rendered, args.output)


def _render_goal_model_text(model: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Goal model #{model['id']} (goal={model['goal_id']}, version={model['version']}, active={model['active']})",
            f"Objective metric: {model['objective_metric']}",
            f"Model type: {model['model_type']}",
            f"Equation: {model['model_equation']}",
            f"Variables: {json.dumps(model.get('variable_definitions') or {}, ensure_ascii=False)}",
            f"Parameters: {json.dumps(model.get('parameter_estimates') or {}, ensure_ascii=False)}",
            f"Thresholds: {json.dumps(model.get('trigger_thresholds') or {}, ensure_ascii=False)}",
        ]
    )


def _render_goal_diagnosis_text(diagnosis: dict[str, Any]) -> str:
    primary = diagnosis.get("primary_component") or {}
    return "\n".join(
        [
            f"Goal diagnosis #{diagnosis['id']} for goal {diagnosis['goal_id']}",
            f"Type: {diagnosis['diagnosis_type']}",
            f"Escalation required: {diagnosis['executive_escalation_required']}",
            f"Primary component: {primary.get('component_name', 'n/a')}",
            f"Hypothesis: {diagnosis['root_cause_hypothesis']}",
        ]
    )


def _render_goal_status_text(payload: dict[str, Any]) -> str:
    goal = payload["goal"]
    model = payload.get("active_model")
    snapshot = payload.get("latest_snapshot") or {}
    forecast = payload.get("latest_forecast") or {}
    diagnostic = payload.get("latest_diagnostic") or {}
    lines = [
        f"Goal #{goal['id']}: {goal['title']}",
        f"Status: {goal['status']}",
        f"Target: {goal['target_metric']} {goal['target_value']} by {goal['deadline']}",
        f"Current value: {goal['current_value']}",
        f"Active model: {model['model_type']} v{model['version']}" if model else "Active model: none",
        f"Latest snapshot health: {snapshot.get('health_status', 'n/a')}",
        f"Latest snapshot variance: {snapshot.get('variance', 'n/a')}",
        f"Probability to hit: {forecast.get('probability_to_hit', 'n/a')}",
        f"Unresolved anomalies: {payload['unresolved_anomalies']}",
        f"Latest diagnosis: {diagnostic.get('root_cause_hypothesis', 'n/a')}",
        f"Next action: {forecast.get('recommended_mode', 'n/a')}",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bridge layer for OpenClaw <-> Codex operations in Harness."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Show bridge and dependency status.")
    status_parser.add_argument("--format", choices=["text", "json"], default="text")
    status_parser.add_argument("--output")
    status_parser.set_defaults(func=command_status)

    card_parser = subparsers.add_parser("decision-card", help="Render a decision card for OpenClaw or mobile.")
    card_parser.add_argument("target_type", choices=["signal", "refined_output", "research_report"])
    card_parser.add_argument("target_id", type=int)
    card_parser.add_argument("--format", choices=["text", "json", "slack-json"], default="json")
    card_parser.add_argument("--output")
    card_parser.set_defaults(func=command_decision_card)

    decision_parser = subparsers.add_parser("record-decision", help="Persist a President decision.")
    decision_parser.add_argument("target_type", choices=sorted(APPROVAL_TARGET_TYPES))
    decision_parser.add_argument("target_id", type=int)
    decision_parser.add_argument("decision", choices=sorted(VALID_DECISIONS))
    decision_parser.add_argument("approval_type", choices=sorted(VALID_APPROVAL_TYPES))
    decision_parser.add_argument("--reason")
    decision_parser.add_argument("--output")
    decision_parser.set_defaults(func=command_record_decision)

    route_parser = subparsers.add_parser("route-note", help="Send a note to a Slack route for OpenClaw-visible ops.")
    route_parser.add_argument("route")
    route_parser.add_argument("text")
    route_parser.add_argument("--output")
    route_parser.set_defaults(func=command_route_note)

    packet_parser = subparsers.add_parser("task-packet", help="Build a structured task packet for OpenClaw routing.")
    packet_parser.add_argument("task_kind")
    packet_parser.add_argument("title")
    packet_parser.add_argument("--executor", default="openclaw")
    packet_parser.add_argument("--objective", required=True)
    packet_parser.add_argument("--input-artifact", action="append")
    packet_parser.add_argument("--output-artifact", action="append")
    packet_parser.add_argument("--check", action="append")
    packet_parser.add_argument("--note", action="append")
    packet_parser.add_argument("--route")
    packet_parser.add_argument("--callback-command")
    packet_parser.add_argument("--output")
    packet_parser.set_defaults(func=command_task_packet)

    ops_parser = subparsers.add_parser("publish-ops-brief", help="Publish OpenClaw ops brief to Slack/Notion and log review.")
    ops_parser.add_argument("--route", default="exec_daily_brief")
    ops_parser.add_argument("--to-slack", action="store_true")
    ops_parser.add_argument("--to-notion", action="store_true")
    ops_parser.add_argument("--summary-text")
    ops_parser.add_argument("--review-type", default="openclaw_daily_ops")
    ops_parser.add_argument("--output")
    ops_parser.set_defaults(func=command_publish_ops_brief)

    push_card_parser = subparsers.add_parser("push-approval-card", help="Send a decision card to the executive Slack route.")
    push_card_parser.add_argument("target_type", choices=["signal", "refined_output", "research_report"])
    push_card_parser.add_argument("target_id", type=int)
    push_card_parser.add_argument("--route", default="exec_president_decisions")
    push_card_parser.add_argument("--output")
    push_card_parser.set_defaults(func=command_push_approval_card)

    dispatch_parser = subparsers.add_parser("dispatch-task-packet", help="Build and dispatch a task packet to Claude/Gemini/Copilot CLIs.")
    dispatch_parser.add_argument("task_kind")
    dispatch_parser.add_argument("title")
    dispatch_parser.add_argument("--objective", required=True)
    dispatch_parser.add_argument("--provider", action="append", choices=["claude", "gemini", "copilot"])
    dispatch_parser.add_argument("--input-artifact", action="append")
    dispatch_parser.add_argument("--output-artifact", action="append")
    dispatch_parser.add_argument("--check", action="append")
    dispatch_parser.add_argument("--note", action="append")
    dispatch_parser.add_argument("--callback-route", default="agent_openclaw_routing")
    dispatch_parser.add_argument("--notify-route", default="agent_openclaw_routing")
    dispatch_parser.add_argument("--output-dir", default="docs/reports/llm_outputs")
    dispatch_parser.add_argument("--output")
    dispatch_parser.set_defaults(func=command_dispatch_task_packet)

    pipeline_parser = subparsers.add_parser("run-pipeline", help="Run the Harness pipeline from the bridge.")
    pipeline_parser.add_argument("--notify-slack", action="store_true")
    pipeline_parser.add_argument("--output")
    pipeline_parser.set_defaults(func=command_run_pipeline)

    goal_create_parser = subparsers.add_parser("goal-create", help="Create a strategic goal artifact.")
    goal_create_parser.add_argument("--title", required=True)
    goal_create_parser.add_argument("--objective", required=True)
    goal_create_parser.add_argument("--target-metric", required=True)
    goal_create_parser.add_argument("--target-value", required=True, type=float)
    goal_create_parser.add_argument("--deadline", required=True)
    goal_create_parser.add_argument("--goal-type", default="growth")
    goal_create_parser.add_argument("--channel")
    goal_create_parser.add_argument("--unit", default="count")
    goal_create_parser.add_argument("--urgency", default="medium")
    goal_create_parser.add_argument("--baseline-value", default=0.0, type=float)
    goal_create_parser.add_argument("--current-value", default=0.0, type=float)
    goal_create_parser.add_argument("--success-definition")
    goal_create_parser.add_argument("--failure-definition")
    goal_create_parser.add_argument("--constraints-json")
    goal_create_parser.add_argument("--metadata-json")
    goal_create_parser.add_argument("--output")
    goal_create_parser.set_defaults(func=command_goal_create)

    goal_model_parser = subparsers.add_parser("goal-model", help="Create or inspect a goal model specification.")
    goal_model_parser.add_argument("goal_id", type=int)
    goal_model_parser.add_argument("--format", choices=["text", "json"], default="text")
    goal_model_parser.add_argument("--model-type", default="deterministic_funnel")
    goal_model_parser.add_argument("--objective-metric")
    goal_model_parser.add_argument("--equation")
    goal_model_parser.add_argument("--variables-json")
    goal_model_parser.add_argument("--parameters-json")
    goal_model_parser.add_argument("--sensitivity-json")
    goal_model_parser.add_argument("--thresholds-json")
    goal_model_parser.add_argument("--assumptions-json")
    goal_model_parser.add_argument("--created-by", default="Business Operations Team")
    goal_model_parser.add_argument("--inactive", action="store_true")
    goal_model_parser.add_argument("--output")
    goal_model_parser.set_defaults(func=command_goal_model)

    goal_snapshot_parser = subparsers.add_parser("goal-snapshot", help="Record a KPI snapshot for a goal.")
    goal_snapshot_parser.add_argument("goal_id", type=int)
    goal_snapshot_parser.add_argument("--actual-value", required=True, type=float)
    goal_snapshot_parser.add_argument("--expected-value", type=float)
    goal_snapshot_parser.add_argument("--forecast-probability", type=float)
    goal_snapshot_parser.add_argument("--health-status", choices=["green", "yellow", "red"], default="green")
    goal_snapshot_parser.add_argument("--notes")
    goal_snapshot_parser.add_argument("--source-metrics-json")
    goal_snapshot_parser.add_argument("--components-json")
    goal_snapshot_parser.add_argument("--snapshot-date")
    goal_snapshot_parser.add_argument("--output")
    goal_snapshot_parser.set_defaults(func=command_goal_snapshot)

    goal_substack_snapshot_parser = subparsers.add_parser(
        "goal-substack-snapshot",
        help="Record a goal snapshot using Substack metrics plus optional growth overrides.",
    )
    goal_substack_snapshot_parser.add_argument("goal_id", type=int)
    goal_substack_snapshot_parser.add_argument("--actual-value", type=float)
    goal_substack_snapshot_parser.add_argument("--expected-value", type=float)
    goal_substack_snapshot_parser.add_argument("--forecast-probability", type=float)
    goal_substack_snapshot_parser.add_argument("--health-status", choices=["green", "yellow", "red"], default="green")
    goal_substack_snapshot_parser.add_argument("--notes")
    goal_substack_snapshot_parser.add_argument("--snapshot-date")
    goal_substack_snapshot_parser.add_argument("--free-subscribers", type=int)
    goal_substack_snapshot_parser.add_argument("--paid-subscribers", type=int)
    goal_substack_snapshot_parser.add_argument("--post-count", type=int)
    goal_substack_snapshot_parser.add_argument("--draft-count", type=int)
    goal_substack_snapshot_parser.add_argument("--followers", type=int)
    goal_substack_snapshot_parser.add_argument("--recommendation-subscribers", type=int)
    goal_substack_snapshot_parser.add_argument("--direct-subscribers", type=int)
    goal_substack_snapshot_parser.add_argument("--welcome-page-visitors", type=int)
    goal_substack_snapshot_parser.add_argument("--welcome-page-conversion-rate", type=float)
    goal_substack_snapshot_parser.add_argument("--note-publish-count", type=int)
    goal_substack_snapshot_parser.add_argument("--output")
    goal_substack_snapshot_parser.set_defaults(func=command_goal_substack_snapshot)

    goal_provider_snapshot_parser = subparsers.add_parser(
        "goal-provider-snapshot",
        help="Record a goal snapshot through a provider adapter. Current pilot adapter: substack.",
    )
    goal_provider_snapshot_parser.add_argument("goal_id", type=int)
    goal_provider_snapshot_parser.add_argument("--provider", required=True)
    goal_provider_snapshot_parser.add_argument("--actual-value", type=float)
    goal_provider_snapshot_parser.add_argument("--expected-value", type=float)
    goal_provider_snapshot_parser.add_argument("--forecast-probability", type=float)
    goal_provider_snapshot_parser.add_argument("--health-status", choices=["green", "yellow", "red"], default="green")
    goal_provider_snapshot_parser.add_argument("--notes")
    goal_provider_snapshot_parser.add_argument("--snapshot-date")
    goal_provider_snapshot_parser.add_argument("--free-subscribers", type=int)
    goal_provider_snapshot_parser.add_argument("--paid-subscribers", type=int)
    goal_provider_snapshot_parser.add_argument("--post-count", type=int)
    goal_provider_snapshot_parser.add_argument("--draft-count", type=int)
    goal_provider_snapshot_parser.add_argument("--followers", type=int)
    goal_provider_snapshot_parser.add_argument("--recommendation-subscribers", type=int)
    goal_provider_snapshot_parser.add_argument("--direct-subscribers", type=int)
    goal_provider_snapshot_parser.add_argument("--welcome-page-visitors", type=int)
    goal_provider_snapshot_parser.add_argument("--welcome-page-conversion-rate", type=float)
    goal_provider_snapshot_parser.add_argument("--note-publish-count", type=int)
    goal_provider_snapshot_parser.add_argument("--output")
    goal_provider_snapshot_parser.set_defaults(func=command_goal_provider_snapshot)

    goal_diagnose_parser = subparsers.add_parser("goal-diagnose", help="Diagnose the primary bottleneck for a goal.")
    goal_diagnose_parser.add_argument("goal_id", type=int)
    goal_diagnose_parser.add_argument("--format", choices=["text", "json"], default="text")
    goal_diagnose_parser.add_argument("--output")
    goal_diagnose_parser.set_defaults(func=command_goal_diagnose)

    goal_status_parser = subparsers.add_parser("goal-status", help="Show current health for a goal, or list all goals if no ID given.")
    goal_status_parser.add_argument("goal_id", type=int, nargs="?", default=None)
    goal_status_parser.add_argument("--format", choices=["text", "json"], default="text")
    goal_status_parser.add_argument("--output")
    goal_status_parser.set_defaults(func=command_goal_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
