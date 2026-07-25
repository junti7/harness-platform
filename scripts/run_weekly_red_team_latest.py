#!/usr/bin/env python3
"""Compatibility tombstone for the retired automatic weekly Red Team."""

import json


def main() -> int:
    print(
        json.dumps(
            {
                "status": "retired",
                "reason": "ceo_order_required",
                "message": (
                    "Automatic weekly Red Team is disabled. "
                    "Use scripts/run_red_team.py with --ceo-order-id."
                ),
                "gate_open": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
