import os
import time

import httpx
from dotenv import load_dotenv

from adapters.content.decision_card import build_decision_card, render_mobile_text
from core.logger import HarnessLogger


load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
MAX_RETRIES = 3


def _truncate(text: str | None, limit: int) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _field(title: str, value) -> dict:
    return {
        "type": "mrkdwn",
        "text": f"*{title}*\n{value if value not in (None, '') else '-'}",
    }


def build_slack_payload(card: dict) -> dict:
    scores = card.get("scores") or {}
    vice_president = card.get("vice_president_feedback") or {}
    ceo = card.get("ceo_decision") or {}
    risks = card.get("top_risks") or []
    evidence = card.get("evidence_links") or []

    score_text = "\n".join(f"{key}: {value}" for key, value in scores.items())
    risk_text = "\n".join(f"- {risk}" for risk in risks[:3]) or "-"
    evidence_text = "\n".join(f"- {link}" for link in evidence[:3]) or "-"
    vice_president_text = (
        f"{vice_president.get('market_read')} | trust={vice_president.get('trust_temperature')} | "
        f"timing={vice_president.get('timing_read')} | action={vice_president.get('requested_action')}"
        if vice_president else "no feedback yet"
    )
    ceo_text = f"{ceo.get('decision')} | {ceo.get('reason') or ''}" if ceo else "no decision yet"

    ceo_commands = "\n".join(
        f"`{action['command']}`" for action in card["mobile_actions"]["ceo"]
    )
    vice_president_commands = "\n".join(
        f"`{action['command']}`" for action in card["mobile_actions"]["vice_president"]
    )

    return {
        "text": f"Harness Decision Card: {card.get('one_line_signal')}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": _truncate(str(card.get("one_line_signal") or "Harness Decision Card"), 140),
                },
            },
            {
                "type": "section",
                "fields": [
                    _field("Target", f"{card['target_type']}#{card['target_id']}"),
                    _field("Recommended Action", card.get("recommended_action")),
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Business Implication*\n{_truncate(card.get('investment_business_implication'), 900)}",
                },
            },
            {
                "type": "section",
                "fields": [
                    _field("Scores", score_text),
                    _field("Vice President", vice_president_text),
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Evidence*\n{evidence_text}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Risks*\n{risk_text}"},
            },
            {
                "type": "section",
                "fields": [
                    _field("CEO Decision", ceo_text),
                    _field("Agent Reviews", _agent_review_text(card)),
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*CEO Commands*\n{ceo_commands}\n\n*Vice President Commands*\n{vice_president_commands}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "OpenClaw can consume the same decision card JSON and map these commands to mobile buttons.",
                    }
                ],
            },
        ],
    }


def _agent_review_text(card: dict) -> str:
    review = card.get("agent_review") or {}
    return (
        f"count={review.get('count')}, "
        f"avg_score={review.get('avg_score')}, "
        f"avg_confidence={review.get('avg_confidence')}"
    )


def send_slack_payload(payload: dict, logger: HarnessLogger):
    if not SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL == "your_webhook_here":
        raise RuntimeError("SLACK_WEBHOOK_URL is not configured")

    for attempt in range(MAX_RETRIES):
        try:
            response = httpx.post(SLACK_WEBHOOK_URL, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Decision card Slack 발송 완료")
            return
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                logger.warning(f"Decision card Slack 재시도 {attempt + 1}/{MAX_RETRIES}: {e}")
                time.sleep(wait)
            else:
                raise


def send_decision_card(target_type: str, target_id: int, channel: str = "slack") -> dict:
    logger = HarnessLogger(tier=4)
    card = build_decision_card(target_type, target_id)

    if channel == "slack":
        payload = build_slack_payload(card)
        send_slack_payload(payload, logger)
        return {"channel": "slack", "sent": True, "card": card}

    if channel == "text":
        return {"channel": "text", "sent": False, "text": render_mobile_text(card), "card": card}

    if channel == "json":
        return {"channel": "json", "sent": False, "card": card}

    raise ValueError("channel must be one of: slack, text, json")
