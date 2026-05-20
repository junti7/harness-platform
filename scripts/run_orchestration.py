"""CLI entry for the Jarvis orchestration loop (adapters/content/orchestrator.py).

Usage:
    python scripts/run_orchestration.py --order "이번 주 paid 전환 실험 하나 설계해줘"
    python scripts/run_orchestration.py --order "..." --dry-run        # plan only, no LLM/post
    python scripts/run_orchestration.py --order "..." --rounds 1 --no-post
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.content.orchestrator import DEFAULT_ROUNDS, orchestrate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Jarvis orchestration loop on a CEO order.")
    parser.add_argument("--order", required=True, help="the CEO order to orchestrate")
    parser.add_argument("--correlation-id", default=None)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="회의실 debate rounds (capped at MAX_CC_HOPS)")
    parser.add_argument("--dry-run", action="store_true", help="show the plan; no LLM call, no Slack post")
    parser.add_argument("--no-post", action="store_true", help="call LLMs but skip Slack posts")
    args = parser.parse_args()

    result = orchestrate(
        args.order,
        args.correlation_id,
        rounds=args.rounds,
        dry_run=args.dry_run,
        post=not args.no_post,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
