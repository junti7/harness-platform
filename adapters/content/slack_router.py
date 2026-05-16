import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()

MAX_RETRIES = 3

ROUTES = {
    "exec_president_decisions": {
        "channel": "#exec-president-decisions",
        "channel_env": "SLACK_CHANNEL_EXEC_PRESIDENT_DECISIONS",
        "webhook_env": "SLACK_WEBHOOK_EXEC_PRESIDENT_DECISIONS",
    },
    "exec_capital_actions": {
        "channel": "#exec-capital-actions",
        "channel_env": "SLACK_CHANNEL_EXEC_CAPITAL_ACTIONS",
        "webhook_env": "SLACK_WEBHOOK_EXEC_CAPITAL_ACTIONS",
    },
    "exec_daily_brief": {
        "channel": "#exec-daily-brief",
        "channel_env": "SLACK_CHANNEL_EXEC_DAILY_BRIEF",
        "webhook_env": "SLACK_WEBHOOK_EXEC_DAILY_BRIEF",
    },
    "vp_content_review": {
        "channel": "#vp-content-review",
        "channel_env": "SLACK_CHANNEL_VP_CONTENT_REVIEW",
        "webhook_env": "SLACK_WEBHOOK_VP_CONTENT_REVIEW",
    },
    "vp_market_read": {
        "channel": "#vp-content-review",
        "channel_env": "SLACK_CHANNEL_VP_CONTENT_REVIEW",
        "webhook_env": "SLACK_WEBHOOK_VP_MARKET_READ",
    },
    "vp_customer_narratives": {
        "channel": "#vp-customer-narratives",
        "channel_env": "SLACK_CHANNEL_VP_CUSTOMER_NARRATIVES",
        "webhook_env": "SLACK_WEBHOOK_VP_CUSTOMER_NARRATIVES",
    },
    "vp_relationship_map": {
        "channel": "#vp-relationship-map",
        "channel_env": "SLACK_CHANNEL_VP_RELATIONSHIP_MAP",
        "webhook_env": "SLACK_WEBHOOK_VP_RELATIONSHIP_MAP",
    },
    "hr_vp_ojt": {
        "channel": "#hr-vp-ojt",
        "channel_env": "SLACK_CHANNEL_HR_VP_OJT",
        "webhook_env": "SLACK_WEBHOOK_HR_VP_OJT",
    },
    "hr_vp_assessments": {
        "channel": "#hr-vp-assessments",
        "channel_env": "SLACK_CHANNEL_HR_VP_ASSESSMENTS",
        "webhook_env": "SLACK_WEBHOOK_HR_VP_ASSESSMENTS",
    },
    "hr_president_reports": {
        "channel": "#hr-president-reports",
        "channel_env": "SLACK_CHANNEL_HR_PRESIDENT_REPORTS",
        "webhook_env": "SLACK_WEBHOOK_HR_PRESIDENT_REPORTS",
    },
    "intel_evidence_feed": {
        "channel": "#intel-evidence-feed",
        "channel_env": "SLACK_CHANNEL_INTEL_EVIDENCE_FEED",
        "webhook_env": "SLACK_WEBHOOK_INTEL_EVIDENCE_FEED",
    },
    "intel_signals": {
        "channel": "#intel-signals",
        "channel_env": "SLACK_CHANNEL_INTEL_SIGNALS",
        "webhook_env": "SLACK_WEBHOOK_INTEL_SIGNALS",
    },
    "intel_opportunities": {
        "channel": "#intel-opportunities",
        "channel_env": "SLACK_CHANNEL_INTEL_OPPORTUNITIES",
        "webhook_env": "SLACK_WEBHOOK_INTEL_OPPORTUNITIES",
    },
    "intel_research_reviews": {
        "channel": "#intel-research-reviews",
        "channel_env": "SLACK_CHANNEL_INTEL_RESEARCH_REVIEWS",
        "webhook_env": "SLACK_WEBHOOK_INTEL_RESEARCH_REVIEWS",
    },
    "revenue_experiments": {
        "channel": "#revenue-experiments",
        "channel_env": "SLACK_CHANNEL_REVENUE_EXPERIMENTS",
        "webhook_env": "SLACK_WEBHOOK_REVENUE_EXPERIMENTS",
    },
    "customer_validation": {
        "channel": "#customer-validation",
        "channel_env": "SLACK_CHANNEL_CUSTOMER_VALIDATION",
        "webhook_env": "SLACK_WEBHOOK_CUSTOMER_VALIDATION",
    },
    "product_reports": {
        "channel": "#product-reports",
        "channel_env": "SLACK_CHANNEL_PRODUCT_REPORTS",
        "webhook_env": "SLACK_WEBHOOK_PRODUCT_REPORTS",
    },
    "eng_codex": {
        "channel": "#eng-codex",
        "channel_env": "SLACK_CHANNEL_ENG_CODEX",
        "webhook_env": "SLACK_WEBHOOK_ENG_CODEX",
    },
    "agent_github_copilot": {
        "channel": "#agent-github-copilot",
        "channel_env": "SLACK_CHANNEL_AGENT_GITHUB_COPILOT",
        "webhook_env": "SLACK_WEBHOOK_AGENT_GITHUB_COPILOT",
    },
    "agent_claude_strategy": {
        "channel": "#agent-claude-strategy",
        "channel_env": "SLACK_CHANNEL_AGENT_CLAUDE_STRATEGY",
        "webhook_env": "SLACK_WEBHOOK_AGENT_CLAUDE_STRATEGY",
    },
    "agent_gemini_research": {
        "channel": "#agent-gemini-research",
        "channel_env": "SLACK_CHANNEL_AGENT_GEMINI_RESEARCH",
        "webhook_env": "SLACK_WEBHOOK_AGENT_GEMINI_RESEARCH",
    },
    "agent_gpt_evaluation": {
        "channel": "#agent-gpt-evaluation",
        "channel_env": "SLACK_CHANNEL_AGENT_GPT_EVALUATION",
        "webhook_env": "SLACK_WEBHOOK_AGENT_GPT_EVALUATION",
    },
    "agent_local_gate": {
        "channel": "#agent-local-gate",
        "channel_env": "SLACK_CHANNEL_AGENT_LOCAL_GATE",
        "webhook_env": "SLACK_WEBHOOK_AGENT_LOCAL_GATE",
    },
    "agent_openclaw_routing": {
        "channel": "#agent-openclaw-routing",
        "channel_env": "SLACK_CHANNEL_AGENT_OPENCLAW_ROUTING",
        "webhook_env": "SLACK_WEBHOOK_AGENT_OPENCLAW_ROUTING",
    },
    "ops_agent_runs": {
        "channel": "#ops-agent-runs",
        "channel_env": "SLACK_CHANNEL_OPS_AGENT_RUNS",
        "webhook_env": "SLACK_WEBHOOK_OPS_AGENT_RUNS",
    },
    "ops_incidents": {
        "channel": "#ops-incidents",
        "channel_env": "SLACK_CHANNEL_OPS_INCIDENTS",
        "webhook_env": "SLACK_WEBHOOK_OPS_INCIDENTS",
    },
    "security_permissions": {
        "channel": "#security-permissions",
        "channel_env": "SLACK_CHANNEL_SECURITY_PERMISSIONS",
        "webhook_env": "SLACK_WEBHOOK_SECURITY_PERMISSIONS",
    },
}

PHASE1_ROUTE_ALIASES = {
    "exec_capital_actions": "exec_president_decisions",
    "exec_daily_brief": "exec_president_decisions",
    "vp_customer_narratives": "vp_content_review",
    "vp_relationship_map": "vp_content_review",
    "hr_vp_ojt": "vp_content_review",
    "hr_vp_assessments": "vp_content_review",
    "hr_president_reports": "exec_president_decisions",
    "intel_evidence_feed": "ops_incidents",
    "intel_signals": "exec_president_decisions",
    "intel_opportunities": "exec_president_decisions",
    "intel_research_reviews": "exec_president_decisions",
    "revenue_experiments": "exec_president_decisions",
    "customer_validation": "vp_content_review",
    "product_reports": "exec_president_decisions",
    "eng_codex": "ops_incidents",
    "agent_github_copilot": "ops_incidents",
    "agent_claude_strategy": "ops_incidents",
    "agent_gemini_research": "ops_incidents",
    "agent_gpt_evaluation": "ops_incidents",
    "agent_local_gate": "ops_incidents",
    "agent_openclaw_routing": "ops_incidents",
    "ops_agent_runs": "ops_incidents",
    "security_permissions": "ops_incidents",
}


def route_label(route: str) -> str:
    active_route = _active_route(route)
    return ROUTES.get(active_route, {}).get("channel", f"#{active_route}")


def send_slack_route(route: str, payload: dict[str, Any]) -> None:
    if route not in ROUTES:
        raise ValueError(f"Unknown Slack route: {route}")

    active_route = _active_route(route)
    routed_payload = _with_phase1_context(route, active_route, payload)
    mode = os.getenv("SLACK_DELIVERY_MODE", "webhook").lower()
    if mode == "bot":
        _send_bot(active_route, routed_payload)
        return

    _send_webhook(active_route, routed_payload)


def _active_route(route: str) -> str:
    if os.getenv("SLACK_PHASE", "phase1").lower() == "phase1":
        return PHASE1_ROUTE_ALIASES.get(route, route)
    return route


def _with_phase1_context(original_route: str, active_route: str, payload: dict[str, Any]) -> dict[str, Any]:
    if original_route == active_route:
        return payload

    original_channel = ROUTES[original_route]["channel"]
    active_channel = ROUTES[active_route]["channel"]
    routed_payload = dict(payload)
    routed_payload["text"] = (
        f"[routed {original_channel} -> {active_channel}] {payload.get('text', '')}"
    ).strip()

    blocks = list(payload.get("blocks") or [])
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Phase 1 routing: `{original_channel}` archived; delivered to `{active_channel}`.",
                }
            ],
        }
    )
    routed_payload["blocks"] = blocks
    return routed_payload


def _send_bot(route: str, payload: dict[str, Any]) -> None:
    token = os.getenv("SLACK_BOT_TOKEN", "")
    channel = os.getenv(ROUTES[route]["channel_env"], "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured")
    if not channel:
        raise RuntimeError(f"{ROUTES[route]['channel_env']} is not configured")

    bot_payload = dict(payload)
    bot_payload["channel"] = channel
    _post(
        "https://slack.com/api/chat.postMessage",
        bot_payload,
        headers={"Authorization": f"Bearer {token}"},
    )


def _send_webhook(route: str, payload: dict[str, Any]) -> None:
    webhook_url = os.getenv(ROUTES[route]["webhook_env"], "") or os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url or webhook_url == "your_webhook_here":
        raise RuntimeError("Slack webhook is not configured")

    webhook_payload = _with_intended_channel(route, payload)
    _post(webhook_url, webhook_payload)


def _with_intended_channel(route: str, payload: dict[str, Any]) -> dict[str, Any]:
    intended_channel = route_label(route)
    routed_payload = dict(payload)
    routed_payload["text"] = f"[{intended_channel}] {payload.get('text', '')}".strip()

    blocks = list(payload.get("blocks") or [])
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Intended route: `{intended_channel}`. Configure Bot Token or route-specific webhook for true channel delivery.",
                }
            ],
        }
    )
    routed_payload["blocks"] = blocks
    return routed_payload


def _post(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> None:
    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
                if data.get("ok") is False:
                    raise RuntimeError(f"Slack API error: {data.get('error')}")
            return
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2**attempt)
