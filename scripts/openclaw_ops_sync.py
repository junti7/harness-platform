import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, ".")

from adapters.content.publisher import publish_notion
from adapters.content.slack_router import route_label, send_slack_route
from core.database import execute_query
from core.logger import HarnessLogger


STATUS_PATH = Path("runtime/openclaw_status.json")


def _load_status(path: Path = STATUS_PATH) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    from scripts.openclaw_codex_bridge import status_snapshot

    return status_snapshot()


def _component_state(label: str, payload: dict[str, Any]) -> tuple[str, bool, str]:
    available = bool(payload.get("available"))
    detail = payload.get("path") or payload.get("error") or "-"
    return label, available, str(detail)


def _status_score(status: dict[str, Any]) -> float:
    integrations = status.get("integrations") or {}
    services = status.get("services") or {}
    integrity = status.get("integrity") or {}
    checks = [
        bool((integrations.get("openclaw") or {}).get("available")),
        bool((integrations.get("ollama") or {}).get("available")),
        bool((integrations.get("postgres") or {}).get("available")),
        bool((integrations.get("slack_webhook") or {}).get("available") or (integrations.get("slack_bot") or {}).get("available")),
        bool((integrations.get("notion") or {}).get("available")),
        bool(services.get("ollama_11434")),
        bool(integrity.get("ok")),
    ]
    return round(sum(1 for ok in checks if ok) / len(checks), 3)


def build_ops_brief(status: dict[str, Any], summary_text: str | None = None) -> dict[str, Any]:
    integrations = status.get("integrations") or {}
    services = status.get("services") or {}
    runtime = status.get("runtime") or {}
    integrity = status.get("integrity") or {}

    component_rows = [
        _component_state("OpenClaw", integrations.get("openclaw") or {}),
        _component_state("Ollama", integrations.get("ollama") or {}),
        _component_state("Postgres", integrations.get("postgres") or {}),
        _component_state("Slack Bot", integrations.get("slack_bot") or {}),
        _component_state("Slack Webhook", integrations.get("slack_webhook") or {}),
        _component_state("Notion", integrations.get("notion") or {}),
    ]

    risks: list[str] = []
    if not (integrations.get("openclaw") or {}).get("available"):
        risks.append("OpenClaw CLI unavailable on 24/7 host.")
    if not (integrations.get("postgres") or {}).get("available"):
        risks.append(f"Postgres degraded: {(integrations.get('postgres') or {}).get('error') or 'unknown'}")
    if not services.get("ollama_11434"):
        risks.append("Ollama port 11434 is not responding.")
    if not (integrations.get("notion") or {}).get("available"):
        risks.append("Notion publishing unavailable.")
    if not ((integrations.get("slack_webhook") or {}).get("available") or (integrations.get("slack_bot") or {}).get("available")):
        risks.append("Slack delivery unavailable.")
    if not integrity.get("ok", False):
        findings = ", ".join((integrity.get("findings") or [])[:3])
        risks.append(f"Schema/env/model integrity check failed: {findings or 'unknown'}")
    if runtime.get("capital_actions_enabled", "false").lower() != "true":
        risks.append("Capital actions remain gated off.")
    if not risks:
        risks.append("No active control-plane degradation detected.")

    top_risks = risks[:3]
    score = _status_score(status)
    health = "green" if score >= 0.83 else "yellow" if score >= 0.5 else "red"

    body_lines = [
        f"Health: {health}",
        f"Generated at: {status.get('generated_at')}",
        f"Slack phase: {runtime.get('slack_phase')}",
        "",
        "Component checks:",
    ]
    for label, available, detail in component_rows:
        body_lines.append(f"- {label}: {'available' if available else 'degraded'} ({detail})")
    body_lines.append(f"- Integrity preflight: {'available' if integrity.get('ok') else 'degraded'}")
    body_lines.extend(["", "Top risks:"])
    body_lines.extend(f"- {risk}" for risk in top_risks)
    if summary_text:
        body_lines.extend(["", "OpenClaw summary:", summary_text.strip()])
    body_lines.extend(
        [
            "",
            "Next action:",
            "- Keep automatic heartbeat active." if health == "green" else "- Review `scripts/openclaw_codex_bridge.py status --format json` and remediate degraded dependencies.",
        ]
    )

    return {
        "title": f"Harness 24/7 Ops Brief - {status.get('generated_at', '')}",
        "summary": f"Health={health}; top risk={top_risks[0]}",
        "body": "\n".join(body_lines),
        "health": health,
        "score": score,
        "risks": top_risks,
        "tags": ["openclaw", "ops", "control-plane", health],
    }


def _build_slack_payload(brief: dict[str, Any], route: str) -> dict[str, Any]:
    risk_text = "\n".join(f"- {risk}" for risk in brief["risks"])
    return {
        "text": f"Harness Ops Brief [{brief['health']}]",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"Harness Ops Brief [{brief['health']}]"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Route*\n{route_label(route)}"},
                    {"type": "mrkdwn", "text": f"*Score*\n{brief['score']}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary*\n{brief['summary']}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Top Risks*\n{risk_text}"},
            },
        ],
    }


def _log_agent_review(brief: dict[str, Any], status: dict[str, Any], review_type: str) -> None:
    execute_query(
        """
        INSERT INTO agent_reviews (
            agent_name, agent_role, model, review_type, score, confidence, reasoning, risks, recommendations, raw_output
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
        """,
        (
            "OpenClaw",
            "control_plane_monitor",
            ((status.get("integrations") or {}).get("openclaw") or {}).get("path") or "openclaw",
            review_type,
            brief["score"],
            0.9,
            brief["summary"],
            json.dumps(brief["risks"], ensure_ascii=False),
            json.dumps(["Escalate only if health is yellow/red."], ensure_ascii=False),
            json.dumps({"status": status, "brief": brief}, ensure_ascii=False),
        ),
    )


def publish_ops_brief(
    route: str,
    to_slack: bool,
    to_notion: bool,
    summary_text: str | None,
    review_type: str,
) -> dict[str, Any]:
    logger = HarnessLogger(tier=4)
    status = _load_status()
    brief = build_ops_brief(status, summary_text=summary_text)

    notion_page_id = None
    notion_error = None
    if to_notion:
        try:
            notion_page_id = publish_notion(
                {
                    "title": brief["title"],
                    "summary": brief["summary"],
                    "body": brief["body"],
                    "tags": brief["tags"],
                    "source": "openclaw_ops_brief",
                },
                logger,
                artifact_type="openclaw_ops_brief",
            )
        except Exception as exc:
            notion_error = str(exc)

    slack_error = None
    if to_slack:
        try:
            send_slack_route(route, _build_slack_payload(brief, route))
        except Exception as exc:
            slack_error = str(exc)

    _log_agent_review(brief, status, review_type)

    return {
        "route": route,
        "slack_sent": to_slack,
        "slack_error": slack_error,
        "notion_page_id": notion_page_id,
        "notion_error": notion_error,
        "health": brief["health"],
        "score": brief["score"],
        "summary": brief["summary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish OpenClaw control-plane ops brief.")
    parser.add_argument("--route", default="exec_daily_brief")
    parser.add_argument("--to-slack", action="store_true")
    parser.add_argument("--to-notion", action="store_true")
    parser.add_argument("--summary-text", default=None)
    parser.add_argument("--review-type", default="openclaw_daily_ops")
    args = parser.parse_args()

    result = publish_ops_brief(
        route=args.route,
        to_slack=args.to_slack,
        to_notion=args.to_notion,
        summary_text=args.summary_text,
        review_type=args.review_type,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
