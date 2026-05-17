"""Canonical key registry for Notion archive.

All callers must use normalize_project() to resolve a project name to its
canonical form before writing to Notion. This prevents "Physical AI Weekly" /
"physical-ai-weekly" / "PAW" drift that breaks LLM retrieval.
"""

from __future__ import annotations

# Maps any known alias (lowercase stripped) → canonical name
_PROJECT_ALIASES: dict[str, str] = {
    "physical ai weekly": "Physical AI Weekly",
    "physical-ai-weekly": "Physical AI Weekly",
    "paw": "Physical AI Weekly",
    "harness": "Harness Platform",
    "harness platform": "Harness Platform",
    "goal loop": "Goal Loop",
    "goal-loop": "Goal Loop",
    "notion archive": "Notion Archive",
    "notion-archive": "Notion Archive",
    "openclaw": "OpenClaw Integration",
    "openclaw integration": "OpenClaw Integration",
}

VALID_ARTIFACT_TYPES = {
    "project",
    "goal",
    "meeting_note",
    "strategy_memo",
    "decision_card",
    "experiment",
    "success_case",
    "failure_case",
    "issue_archive",
    "research_report",
    "sop",
    "ops_brief",
}

VALID_TEAMS = {
    "Chief of Staff",
    "Business Operations",
    "Marketing Strategy",
    "Subscriber Growth",
    "Sales",
    "Product Planning",
    "Vice President Review",
    "Red Team",
    "Legal Counsel",
    "QA",
    "Engineering",
}

# Required for all artifact types
REQUIRED_FIELDS = {"title", "artifact_type", "teams", "summary", "canonical_key"}

# Required per artifact type (in addition to REQUIRED_FIELDS)
TYPE_REQUIRED_FIELDS: dict[str, set[str]] = {
    "decision_card": {"decision_summary", "outcome"},
    "failure_case": {"lessons_learned", "outcome"},
    "success_case": {"lessons_learned", "outcome"},
    "strategy_memo": {"decision_summary"},
    "experiment": {"outcome"},
    "meeting_note": {"action_items"},
}


def normalize_project(name: str | None) -> str | None:
    if not name:
        return None
    key = name.strip().lower()
    return _PROJECT_ALIASES.get(key, name.strip())


def validate_archive_entry(
    *,
    title: str,
    artifact_type: str,
    teams: list[str],
    summary: str | None,
    canonical_key: str | None,
    decision_summary: str | None = None,
    lessons_learned: str | None = None,
    outcome: str | None = None,
    action_items: str | None = None,
) -> list[str]:
    """Returns a list of validation errors. Empty = valid."""
    errors: list[str] = []

    if not title or not title.strip():
        errors.append("title은 필수입니다.")
    if artifact_type not in VALID_ARTIFACT_TYPES:
        errors.append(f"artifact_type '{artifact_type}'은 유효하지 않습니다. 허용값: {sorted(VALID_ARTIFACT_TYPES)}")
    if not teams:
        errors.append("teams는 최소 1개 필요합니다.")
    else:
        invalid_teams = [t for t in teams if t not in VALID_TEAMS]
        if invalid_teams:
            errors.append(f"유효하지 않은 team: {invalid_teams}. 허용값: {sorted(VALID_TEAMS)}")
    if not summary or not summary.strip():
        errors.append("summary는 필수입니다. (1~2줄 핵심 요약)")
    if not canonical_key or not canonical_key.strip():
        errors.append("canonical_key는 필수입니다. (예: 'strategy-memo-2026-05-17-goal-loop')")

    type_required = TYPE_REQUIRED_FIELDS.get(artifact_type, set())
    for field in type_required:
        val = locals().get(field)
        if not val or not str(val).strip():
            errors.append(f"{artifact_type} 타입은 '{field}'가 필수입니다.")

    return errors
