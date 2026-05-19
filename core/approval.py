import os
from typing import Optional


VALID_DECISIONS = {"approved", "hold", "rejected", "request_more_research"}

# high-impact approval_type → 먼저 기록되어야 할 prerequisite approval_types
# CLAUDE.md: "다음 high-impact 결정은 legal_review_approve, red_team_clear, pre_mortem_approve를 사전 조건으로 요구한다"
PREREQUISITE_GATES: dict[str, frozenset[str]] = {
    "report_publish_approve": frozenset({"legal_review_approve", "red_team_clear", "pre_mortem_approve", "qa_clear"}),
    "monetization_experiment_approve": frozenset({"legal_review_approve", "red_team_clear", "pre_mortem_approve", "qa_clear"}),
    "investment_thesis_approve": frozenset({"legal_review_approve", "red_team_clear", "pre_mortem_approve", "qa_clear"}),
    "capital_action_approve": frozenset({"legal_review_approve", "red_team_clear", "pre_mortem_approve"}),
}

VALID_APPROVAL_TYPES = {
    "signal_approve",
    "opportunity_approve",
    "vice_president_review_request",
    "customer_test_approve",
    "monetization_experiment_approve",
    "report_publish_approve",
    "investment_thesis_approve",
    "capital_action_approve",
    "legal_review_approve",
    "red_team_clear",
    "pre_mortem_approve",
    "qa_clear",
}

APPROVAL_TARGET_TYPES = {
    "signal",
    "business_opportunity",
    "customer_hypothesis",
    "monetization_experiment",
    "research_report",
    "newsletter_issue",
    "content_review",
    "investment_thesis",
    "capital_action",
    "refined_output",
    "legal_review",
    "red_team_review",
    "pre_mortem",
    "qa_review",
}


def capital_actions_enabled() -> bool:
    return os.getenv("CAPITAL_ACTIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def validate_decision(decision: str) -> None:
    if decision not in VALID_DECISIONS:
        raise ValueError(f"decision must be one of: {', '.join(sorted(VALID_DECISIONS))}")


def validate_approval(target_type: str, approval_type: str) -> None:
    if target_type not in APPROVAL_TARGET_TYPES:
        raise ValueError(f"target_type must be one of: {', '.join(sorted(APPROVAL_TARGET_TYPES))}")
    if approval_type not in VALID_APPROVAL_TYPES:
        raise ValueError(f"approval_type must be one of: {', '.join(sorted(VALID_APPROVAL_TYPES))}")
    if approval_type == "capital_action_approve" and target_type != "capital_action":
        raise ValueError("capital_action_approve requires target_type=capital_action")
    if target_type == "capital_action" and approval_type != "capital_action_approve":
        raise ValueError("target_type=capital_action requires approval_type=capital_action_approve")
    if approval_type == "capital_action_approve" and not capital_actions_enabled():
        raise PermissionError("CAPITAL_ACTIONS_ENABLED must be true before recording capital_action_approve")
