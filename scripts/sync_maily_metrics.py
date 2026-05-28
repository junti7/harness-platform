"""
Maily metrics -> subscriber_snapshots sync

Usage:
  python scripts/sync_maily_metrics.py
  python scripts/sync_maily_metrics.py --date 2026-05-23
  python scripts/sync_maily_metrics.py --free 120 --opens 950 --clicks 37
  python scripts/sync_maily_metrics.py --json data/maily_metrics.json
  python scripts/sync_maily_metrics.py --csv data/maily_metrics.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from adapters.content.maily_adapter import fetch_subscriber_metrics
from core.database import execute_query
from core.logger import HarnessLogger


def upsert_snapshot(
    *,
    snapshot_date: str,
    platform: str,
    metrics: dict[str, int | str | None],
) -> int | None:
    existing = execute_query(
        "SELECT id FROM subscriber_snapshots WHERE snapshot_date = %s AND platform = %s",
        (snapshot_date, platform),
        fetch=True,
    )
    values = (
        metrics.get("free_subscribers") or 0,
        metrics.get("paid_subscribers") or 0,
        metrics.get("paid_revenue_krw") or 0,
        metrics.get("opens") or 0,
        metrics.get("clicks") or 0,
        metrics.get("replies") or 0,
        metrics.get("shares") or 0,
        metrics.get("unsubscribe_count") or 0,
        str(metrics.get("notes") or ""),
    )
    if existing:
        execute_query(
            """
            UPDATE subscriber_snapshots
            SET free_subscribers = %s,
                paid_subscribers = %s,
                paid_revenue_krw = %s,
                opens = %s,
                clicks = %s,
                replies = %s,
                shares = %s,
                unsubscribe_count = %s,
                notes = %s
            WHERE id = %s
            """,
            (*values, existing[0]["id"]),
        )
        return int(existing[0]["id"])

    inserted = execute_query(
        """
        INSERT INTO subscriber_snapshots (
            snapshot_date,
            platform,
            free_subscribers,
            paid_subscribers,
            paid_revenue_krw,
            opens,
            clicks,
            replies,
            shares,
            unsubscribe_count,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (snapshot_date, platform, *values),
        fetch=True,
    )
    return int(inserted[0]["id"]) if inserted else None


def _apply_overrides(metrics: dict[str, int | str | None], args: argparse.Namespace) -> dict[str, int | str | None]:
    override_keys = (
        "free_subscribers",
        "paid_subscribers",
        "paid_revenue_krw",
        "opens",
        "clicks",
        "replies",
        "shares",
        "unsubscribe_count",
    )
    updated = dict(metrics)
    for key in override_keys:
        value = getattr(args, key)
        if value is not None:
            updated[key] = value
    if args.notes is not None:
        updated["notes"] = args.notes
    return updated


def _load_json_overrides(path_value: str) -> dict[str, int | str | None]:
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = (Path(__file__).resolve().parent.parent / path).resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Maily metrics -> subscriber_snapshots sync")
    parser.add_argument("--date", default=str(date.today()), help="snapshot date (YYYY-MM-DD)")
    parser.add_argument("--json", help="JSON metrics file path")
    parser.add_argument("--csv", help="CSV metrics file path")
    parser.add_argument("--free", dest="free_subscribers", type=int)
    parser.add_argument("--paid", dest="paid_subscribers", type=int)
    parser.add_argument("--revenue-krw", dest="paid_revenue_krw", type=int)
    parser.add_argument("--opens", type=int)
    parser.add_argument("--clicks", type=int)
    parser.add_argument("--replies", type=int)
    parser.add_argument("--shares", type=int)
    parser.add_argument("--unsubscribes", dest="unsubscribe_count", type=int)
    parser.add_argument("--notes")
    args = parser.parse_args()

    logger = HarnessLogger(tier=4, correlation_id="maily-metrics-sync")

    if args.csv:
        import os

        os.environ["MAILY_METRICS_CSV_PATH"] = args.csv
        metrics = fetch_subscriber_metrics(logger)
        metrics["notes"] = str(metrics.get("notes") or f"csv input: {args.csv}")
    elif args.json:
        metrics = _load_json_overrides(args.json)
        metrics.setdefault("notes", "json input")
    else:
        metrics = fetch_subscriber_metrics(logger)
    metrics = _apply_overrides(metrics, args)

    snapshot_id = upsert_snapshot(
        snapshot_date=args.date,
        platform="maily",
        metrics=metrics,
    )

    logger.info(f"Maily subscriber_snapshots upserted: id={snapshot_id}")
    print(
        json.dumps(
            {
                "snapshot_id": snapshot_id,
                "snapshot_date": args.date,
                "platform": "maily",
                "metrics": metrics,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
