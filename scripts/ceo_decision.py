import argparse
import sys
from typing import Optional

sys.path.insert(0, ".")

from core.approval import (
    APPROVAL_TARGET_TYPES,
    PREREQUISITE_GATES,
    VALID_APPROVAL_TYPES,
    VALID_DECISIONS,
    validate_approval,
    validate_decision,
)
from core.database import execute_query


def _check_prerequisites(target_type: str, target_id: int, approval_type: str) -> list[str]:
    """Returns sorted list of prerequisite approval_types not yet 'approved' for this target."""
    required = PREREQUISITE_GATES.get(approval_type)
    if not required:
        return []
    rows = execute_query(
        """
        SELECT approval_type FROM ceo_decisions
        WHERE target_type = %s AND target_id = %s
          AND decision = 'approved'
          AND approval_type = ANY(%s)
        """,
        (target_type, target_id, list(required)),
        fetch=True,
    ) or []
    recorded = {r["approval_type"] for r in rows}
    return sorted(required - recorded)


def record_decision(
    target_type: str,
    target_id: int,
    decision: str,
    approval_type: str,
    reason: Optional[str],
):
    validate_decision(decision)
    validate_approval(target_type, approval_type)

    if decision == "approved":
        missing = _check_prerequisites(target_type, target_id, approval_type)
        if missing:
            raise PermissionError(
                f"❌ {approval_type} 기록 전 다음 prerequisite gate가 먼저 'approved'로 기록되어야 합니다:\n"
                + "\n".join(f"  • {g}" for g in missing)
                + f"\n\nrecord-decision {target_type} {target_id} approved <gate> --reason '...' 로 각 gate를 먼저 통과하세요."
            )

    execute_query(
        """
        INSERT INTO ceo_decisions (target_type, target_id, decision, approval_type, reason)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (target_type, target_id, decision)
        DO UPDATE SET
            approval_type = EXCLUDED.approval_type,
            reason = EXCLUDED.reason,
            created_at = NOW()
        """,
        (target_type, target_id, decision, approval_type, reason),
    )


def main():
    parser = argparse.ArgumentParser(description="Record a CEO decision for a publishable item.")
    parser.add_argument("target_type", choices=sorted(APPROVAL_TARGET_TYPES))
    parser.add_argument("target_id", type=int)
    parser.add_argument("decision", choices=sorted(VALID_DECISIONS))
    parser.add_argument("approval_type", choices=sorted(VALID_APPROVAL_TYPES))
    parser.add_argument("--reason", default=None)
    args = parser.parse_args()

    record_decision(args.target_type, args.target_id, args.decision, args.approval_type, args.reason)
    print(
        "Recorded CEO decision: "
        f"{args.target_type}#{args.target_id} -> {args.decision} ({args.approval_type})"
    )


if __name__ == "__main__":
    main()
