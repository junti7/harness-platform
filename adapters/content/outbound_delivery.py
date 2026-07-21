"""Single user-visible text delivery boundary for OpenClaw Slack surfaces."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from core.openclaw_response_quality import DeliveryDecision, SCHEMA_VERSION, VerifiedText


_SECRET_RE = re.compile(
    r"\b(?:xox[abprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|CANARY_SECRET_[A-Za-z0-9_-]+)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OutboundEnvelope:
    channel: str
    audience: Literal["requester_dm", "approved_channel", "internal_error"]
    decision: DeliveryDecision
    idempotency_key: str
    thread_ts: str | None = None


def decision_from_verified_text(value: str) -> DeliveryDecision:
    if not isinstance(value, VerifiedText):
        raise ValueError("unverified outbound text")
    return value.decision


def prepare_outbound(envelope: OutboundEnvelope) -> str:
    decision = envelope.decision
    if decision.schema_version != SCHEMA_VERSION:
        raise ValueError("unsupported delivery decision schema")
    if decision.verdict not in {"deliver", "partial", "abstain"}:
        raise ValueError("invalid delivery verdict")
    text = decision.rendered_text.strip()
    if not text:
        raise ValueError("empty outbound text")
    if _SECRET_RE.search(text):
        raise ValueError("secret detected in outbound text")
    return text


def post_slack(client: Any, envelope: OutboundEnvelope) -> Any:
    payload: dict[str, Any] = {"channel": envelope.channel, "text": prepare_outbound(envelope)}
    if envelope.thread_ts:
        payload["thread_ts"] = envelope.thread_ts
    return client.chat_postMessage(**payload)


def post_slack_token(token: str, envelope: OutboundEnvelope) -> dict[str, Any]:
    payload: dict[str, Any] = {"channel": envelope.channel, "text": prepare_outbound(envelope)}
    if envelope.thread_ts:
        payload["thread_ts"] = envelope.thread_ts
    response = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
        timeout=15.0,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Slack delivery failed: {result.get('error', 'unknown_error')}")
    return result
