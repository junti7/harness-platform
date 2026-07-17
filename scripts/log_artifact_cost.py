#!/usr/bin/env python3
"""Record image/render/QA production usage in artifact_cost_log."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.artifact_costs import log_artifact_cost


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--job-id", required=True)
    p.add_argument("--artifact-type", required=True, choices=["image_generation", "render", "qa", "design"])
    p.add_argument("--provider", required=True)
    p.add_argument("--model")
    p.add_argument("--units", type=float, default=1)
    p.add_argument("--unit-name", default="call")
    p.add_argument("--unit-price-usd", type=float)
    p.add_argument("--actual-cost-usd", type=float)
    p.add_argument("--metadata", default="{}")
    args = p.parse_args()
    log_artifact_cost(
        job_id=args.job_id, artifact_type=args.artifact_type, provider=args.provider,
        model=args.model, units=args.units, unit_name=args.unit_name,
        unit_price_usd=args.unit_price_usd, actual_cost_usd=args.actual_cost_usd,
        metadata=json.loads(args.metadata),
    )
    print(f"logged artifact cost: {args.job_id}/{args.artifact_type}")


if __name__ == "__main__":
    main()
