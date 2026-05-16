import argparse
import json
import sys

sys.path.insert(0, ".")

from adapters.content.red_team import run_weekly_red_team
from core.database import execute_query


def _latest_target() -> tuple[str, int] | None:
    rows = execute_query(
        """
        SELECT id
        FROM research_reports
        WHERE published = FALSE
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
        """,
        fetch=True,
    )
    if rows:
        return "research_report", int(rows[0]["id"])

    rows = execute_query(
        """
        SELECT id
        FROM newsletter_issues
        WHERE status IN ('draft', 'review')
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
        """,
        fetch=True,
    )
    if rows:
        return "newsletter_issue", int(rows[0]["id"])

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run weekly 3-model red-team on the latest review target.")
    parser.add_argument("--target-type", choices=["research_report", "newsletter_issue", "refined_output"], default=None)
    parser.add_argument("--target-id", type=int, default=None)
    parser.add_argument("--provider", action="append", dest="providers")
    parser.add_argument("--reject-issue", action="append", default=[])
    parser.add_argument("--president-confirm-reason", default=None)
    args = parser.parse_args()

    if args.target_type and args.target_id:
        target_type, target_id = args.target_type, args.target_id
    elif args.target_type or args.target_id:
        raise ValueError("--target-type and --target-id must be used together")
    else:
        latest = _latest_target()
        if latest is None:
            result = {
                "status": "skipped",
                "reason": "no_review_target",
                "message": "No draft research_report or newsletter_issue available for weekly red team.",
                "gate_open": False,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        target_type, target_id = latest

    result = run_weekly_red_team(
        target_type=target_type,
        target_id=target_id,
        providers=args.providers,
        president_confirm_reason=args.president_confirm_reason,
        reject_issue_patterns=args.reject_issue,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["gate_open"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
