import argparse
import json
import sys

sys.path.insert(0, ".")

from adapters.content.red_team import run_red_team


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cross-LLM red team gate.")
    parser.add_argument("--target-type", required=True, choices=["newsletter_issue", "refined_output", "research_report"])
    parser.add_argument("--target-id", required=True, type=int)
    parser.add_argument("--ceo-order-id", required=True)
    parser.add_argument("--force-revalidate", action="store_true")
    args = parser.parse_args()

    result = run_red_team(
        args.target_type,
        args.target_id,
        ceo_order_id=args.ceo_order_id,
        force_revalidate=args.force_revalidate,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["decision"] == "red_team_clear" else 1


if __name__ == "__main__":
    raise SystemExit(main())
