import argparse
import json
import sys

sys.path.insert(0, ".")

from adapters.content.red_team import run_weekly_red_team


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the weekly 3-model red-team governance gate.")
    parser.add_argument("--target-type", required=True, choices=["newsletter_issue", "refined_output", "research_report"])
    parser.add_argument("--target-id", required=True, type=int)
    parser.add_argument("--provider", action="append", dest="providers")
    parser.add_argument("--reject-issue", action="append", default=[], help="Substring pattern of issue(s) President rejects")
    parser.add_argument("--president-confirm-reason", default=None)
    args = parser.parse_args()

    result = run_weekly_red_team(
        target_type=args.target_type,
        target_id=args.target_id,
        providers=args.providers,
        president_confirm_reason=args.president_confirm_reason,
        reject_issue_patterns=args.reject_issue,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["gate_open"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
