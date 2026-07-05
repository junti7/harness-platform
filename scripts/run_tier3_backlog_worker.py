import argparse
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from adapters.content.refiner import refine
from core.database import execute_query
from core.logger import HarnessLogger


def pending_count() -> int:
    rows = execute_query(
        """
        SELECT count(*) AS cnt
        FROM filtered_signals f
        WHERE NOT EXISTS (
            SELECT 1 FROM refined_outputs r WHERE r.filtered_signal_id = f.id
        )
        """,
        fetch=True,
    )
    return int((rows or [{"cnt": 0}])[0]["cnt"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Tier 3 backlog worker")
    parser.add_argument("--max-batches", type=int, default=2)
    parser.add_argument("--min-pending", type=int, default=1)
    args = parser.parse_args()

    cid = f"tier3-{str(uuid.uuid4())[:8]}"
    logger = HarnessLogger(tier=3, correlation_id=cid)
    logger.info(f"=== Tier 3 backlog worker 시작 (max_batches={args.max_batches}) ===")

    if os.getenv("PAID_TIER3_BACKLOG_ENABLED", "").strip().lower() != "true":
        logger.warning(
            "paid Tier3 backlog worker disabled; set PAID_TIER3_BACKLOG_ENABLED=true to run"
        )
        return

    before_start = pending_count()
    if before_start < args.min_pending:
        logger.info(
            f"pending {before_start} < min_pending {args.min_pending} — 실행 생략"
        )
        return

    total_refined = 0
    for batch_no in range(1, args.max_batches + 1):
        before = pending_count()
        if before <= 0:
            logger.info("pending 없음 — 종료")
            break
        refined = int(refine(correlation_id=cid) or 0)
        total_refined += refined
        after = pending_count()
        logger.info(f"[batch {batch_no}] pending {before} -> {after}, refined={refined}")
        if after >= before:
            logger.info("pending 감소 없음 — 이번 실행 종료")
            break

    logger.info(f"=== Tier 3 backlog worker 종료 | total_refined={total_refined} ===")


if __name__ == "__main__":
    main()
