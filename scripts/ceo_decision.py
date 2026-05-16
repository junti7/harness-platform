import argparse
import sys
from typing import Optional

sys.path.insert(0, ".")

from core.approval import (
    APPROVAL_TARGET_TYPES,
    VALID_APPROVAL_TYPES,
    VALID_DECISIONS,
    validate_approval,
    validate_decision,
)
from core.database import execute_query


def record_decision(
    target_type: str,
    target_id: int,
    decision: str,
    approval_type: str,
    reason: Optional[str],
):
    validate_decision(decision)
    validate_approval(target_type, approval_type)

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
