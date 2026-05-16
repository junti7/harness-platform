import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from core.database import execute_query


CEO_ACTIONS = ["approved", "rejected", "hold", "request_more_research"]
VICE_PRESIDENT_ACTIONS = ["hot", "unclear", "weak", "relationship_opportunity"]


def _json_default(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _as_dict(row) -> dict | None:
    return dict(row) if row else None


def _latest_partner_feedback(target_type: str, target_id: int) -> dict | None:
    rows = execute_query("""
        SELECT *
        FROM partner_feedback
        WHERE target_type = %s AND target_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (target_type, target_id), fetch=True)
    return _as_dict(rows[0]) if rows else None


def _latest_ceo_decision(target_type: str, target_id: int) -> dict | None:
    rows = execute_query("""
        SELECT *
        FROM ceo_decisions
        WHERE target_type = %s AND target_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (target_type, target_id), fetch=True)
    return _as_dict(rows[0]) if rows else None


def _agent_review_summary(signal_id: int | None = None, refined_output_id: int | None = None) -> dict:
    if signal_id is None and refined_output_id is None:
        return {"count": 0, "avg_score": None, "avg_confidence": None, "latest_risks": []}

    rows = execute_query("""
        SELECT score, confidence, risks, agent_name, review_type, created_at
        FROM agent_reviews
        WHERE (%s IS NULL OR signal_id = %s)
          AND (%s IS NULL OR refined_output_id = %s)
        ORDER BY created_at DESC
    """, (signal_id, signal_id, refined_output_id, refined_output_id), fetch=True)

    if not rows:
        return {"count": 0, "avg_score": None, "avg_confidence": None, "latest_risks": []}

    scores = [float(row["score"]) for row in rows if row.get("score") is not None]
    confidences = [float(row["confidence"]) for row in rows if row.get("confidence") is not None]
    latest_risks = rows[0].get("risks") or []

    return {
        "count": len(rows),
        "avg_score": round(sum(scores) / len(scores), 3) if scores else None,
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
        "latest_risks": latest_risks,
        "latest_review_type": rows[0].get("review_type"),
        "latest_agent": rows[0].get("agent_name"),
    }


def _signal_card(target_id: int) -> dict:
    rows = execute_query("""
        SELECT
            s.*,
            fs.title AS source_title,
            fs.summary AS filtered_summary,
            fs.score AS tier2_score
        FROM signals s
        LEFT JOIN filtered_signals fs ON fs.id = s.filtered_signal_id
        WHERE s.id = %s
        LIMIT 1
    """, (target_id,), fetch=True)
    if not rows:
        raise ValueError(f"signal not found: {target_id}")

    signal = dict(rows[0])
    partner = _latest_partner_feedback("signal", target_id)
    ceo = _latest_ceo_decision("signal", target_id)
    reviews = _agent_review_summary(signal_id=target_id)

    return {
        "target_type": "signal",
        "target_id": target_id,
        "audience": "ceo_partner_mobile",
        "one_line_signal": signal.get("source_title") or signal.get("signal_summary"),
        "recommended_action": _recommended_action(signal, partner),
        "investment_business_implication": _business_implication(signal),
        "evidence_links": _compact_links([signal.get("source_url")]),
        "top_risks": _risk_list(reviews, partner),
        "scores": {
            "preliminary": signal.get("preliminary_score"),
            "novelty": signal.get("novelty_score"),
            "relevance": signal.get("relevance_score"),
            "source_confidence": signal.get("source_confidence"),
            "monetization": signal.get("monetization_potential"),
        },
        "agent_review": reviews,
        "vice_president_feedback": partner,
        "ceo_decision": ceo,
        "mobile_actions": _mobile_actions("signal", target_id),
        "raw": {"signal": signal},
    }


def _refined_output_card(target_id: int) -> dict:
    rows = execute_query("""
        SELECT
            ro.*,
            fs.title AS source_title,
            fs.summary AS filtered_summary,
            fs.score AS tier2_score,
            fs.source,
            fs.content_hash,
            rs.raw_data->>'url' AS source_url,
            s.id AS signal_id,
            s.preliminary_score,
            s.monetization_potential
        FROM refined_outputs ro
        JOIN filtered_signals fs ON fs.id = ro.filtered_signal_id
        LEFT JOIN raw_signals rs ON rs.id = fs.raw_signal_id
        LEFT JOIN signals s ON s.filtered_signal_id = fs.id
        WHERE ro.id = %s
        LIMIT 1
    """, (target_id,), fetch=True)
    if not rows:
        raise ValueError(f"refined_output not found: {target_id}")

    item = dict(rows[0])
    partner = _latest_partner_feedback("refined_output", target_id)
    ceo = _latest_ceo_decision("refined_output", target_id)
    reviews = _agent_review_summary(
        signal_id=item.get("signal_id"),
        refined_output_id=target_id,
    )

    return {
        "target_type": "refined_output",
        "target_id": target_id,
        "audience": "ceo_mobile",
        "one_line_signal": item.get("final_title") or item.get("source_title"),
        "recommended_action": _recommended_action(item, partner),
        "investment_business_implication": item.get("final_body"),
        "evidence_links": _compact_links([item.get("source_url")]),
        "top_risks": _risk_list(reviews, partner),
        "scores": {
            "tier2": item.get("tier2_score"),
            "preliminary": item.get("preliminary_score"),
            "monetization": item.get("monetization_potential"),
        },
        "sensitivity": {
            "level": item.get("sensitivity_level"),
            "requires_ceo_approval": item.get("requires_ceo_approval"),
        },
        "agent_review": reviews,
        "vice_president_feedback": partner,
        "ceo_decision": ceo,
        "mobile_actions": _mobile_actions("refined_output", target_id),
        "raw": {"refined_output": item},
    }


def _research_report_card(target_id: int) -> dict:
    rows = execute_query("""
        SELECT *
        FROM research_reports
        WHERE id = %s
        LIMIT 1
    """, (target_id,), fetch=True)
    if not rows:
        raise ValueError(f"research_report not found: {target_id}")

    report = dict(rows[0])
    partner = _latest_partner_feedback("research_report", target_id)
    ceo = _latest_ceo_decision("research_report", target_id)

    return {
        "target_type": "research_report",
        "target_id": target_id,
        "audience": "ceo_mobile",
        "one_line_signal": report.get("title"),
        "recommended_action": "approve_paid_or_external_release"
        if report.get("requires_ceo_approval") else "review_report",
        "investment_business_implication": report.get("summary") or _truncate(report.get("body"), 500),
        "evidence_links": [],
        "top_risks": [],
        "scores": {"cost_usd": report.get("cost_usd")},
        "sensitivity": {
            "level": report.get("sensitivity_level"),
            "requires_ceo_approval": report.get("requires_ceo_approval"),
        },
        "agent_review": {"count": 0, "avg_score": None, "avg_confidence": None},
        "vice_president_feedback": partner,
        "ceo_decision": ceo,
        "mobile_actions": _mobile_actions("research_report", target_id),
        "raw": {"research_report": report},
    }


def _recommended_action(item: dict, partner: dict | None) -> str:
    if partner:
        if partner.get("requested_action") and partner["requested_action"] != "none":
            return partner["requested_action"]
        if partner.get("market_read") == "hot":
            return "ceo_review"
        if partner.get("market_read") == "relationship_opportunity":
            return "outreach_material"

    monetization = float(item.get("monetization_potential") or 0.0)
    preliminary = float(item.get("preliminary_score") or item.get("tier2_score") or 0.0)
    if monetization >= 0.5 or preliminary >= 0.75:
        return "deep_research"
    if preliminary >= 0.55:
        return "watch"
    return "hold"


def _business_implication(signal: dict) -> str:
    signal_type = signal.get("signal_type") or "news"
    monetization = signal.get("monetization_potential")
    return (
        f"Signal type={signal_type}; monetization_potential={monetization}. "
        "Use this to decide whether deeper research, outreach, or report packaging is justified."
    )


def _risk_list(reviews: dict, partner: dict | None) -> list[str]:
    risks = reviews.get("latest_risks") or []
    if isinstance(risks, str):
        try:
            risks = json.loads(risks)
        except json.JSONDecodeError:
            risks = [risks]

    result = [str(risk) for risk in risks[:3]]
    if partner and partner.get("buyer_hesitation"):
        result.append(f"Vice President buyer hesitation: {partner['buyer_hesitation']}")
    if not result:
        result.append("No explicit risk review yet; treat as unverified.")
    return result[:3]


def _compact_links(links: list[str | None]) -> list[str]:
    return [link for link in links if link][:3]


def _mobile_actions(target_type: str, target_id: int) -> dict:
    approval_type = _default_approval_type(target_type)
    return {
        "ceo": [
            {
                "label": action,
                "command": f"ceo_decision {target_type} {target_id} {action} {approval_type}",
            }
            for action in CEO_ACTIONS
        ],
        "vice_president": [
            {"label": action, "command": f"partner_feedback {target_type} {target_id} {action}"}
            for action in VICE_PRESIDENT_ACTIONS
        ],
    }


def _default_approval_type(target_type: str) -> str:
    if target_type == "signal":
        return "signal_approve"
    if target_type in {"refined_output", "research_report"}:
        return "report_publish_approve"
    return "opportunity_approve"


def _truncate(text: str | None, limit: int) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 3] + "..."


def build_decision_card(target_type: str, target_id: int) -> dict:
    if target_type == "signal":
        return _signal_card(target_id)
    if target_type == "refined_output":
        return _refined_output_card(target_id)
    if target_type == "research_report":
        return _research_report_card(target_id)
    raise ValueError("target_type must be one of: signal, refined_output, research_report")


def render_mobile_text(card: dict) -> str:
    vice_president = card.get("vice_president_feedback") or {}
    ceo = card.get("ceo_decision") or {}
    scores = card.get("scores") or {}

    lines = [
        f"[{card['target_type']}#{card['target_id']}] {card.get('one_line_signal')}",
        f"Action: {card.get('recommended_action')}",
        f"Implication: {_truncate(card.get('investment_business_implication'), 420)}",
        f"Scores: {json.dumps(scores, ensure_ascii=False, default=_json_default)}",
    ]

    if card.get("evidence_links"):
        lines.append("Evidence:")
        lines.extend(f"- {link}" for link in card["evidence_links"])

    lines.append("Risks:")
    lines.extend(f"- {risk}" for risk in card.get("top_risks", []))

    if vice_president:
        lines.append(
            "Vice President: "
            f"{vice_president.get('market_read')} | trust={vice_president.get('trust_temperature')} | "
            f"timing={vice_president.get('timing_read')} | action={vice_president.get('requested_action')}"
        )
        if vice_president.get("analog_notes"):
            lines.append(f"Vice President notes: {_truncate(vice_president.get('analog_notes'), 220)}")
    else:
        lines.append("Vice President: no feedback yet")

    if ceo:
        lines.append(f"CEO: {ceo.get('decision')} | {ceo.get('reason') or ''}")
    else:
        lines.append("CEO: no decision yet")

    lines.append("CEO buttons: Approve / Reject / Hold / More Research")
    lines.append("Vice President buttons: Hot / Unclear / Weak / Relationship Opportunity")
    return "\n".join(lines)


def card_to_json(card: dict) -> str:
    return json.dumps(card, ensure_ascii=False, indent=2, default=_json_default)
