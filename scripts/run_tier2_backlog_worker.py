import argparse
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from adapters.content.filter import filter_signals, probe_ollama_host, OLLAMA_REMOTE_HOST
from core.database import execute_query
from core.logger import HarnessLogger


def pending_count() -> int:
    rows = execute_query("SELECT count(*) AS cnt FROM raw_signals WHERE status = 'pending'", fetch=True)
    return int((rows or [{"cnt": 0}])[0]["cnt"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Tier 2 backlog worker")
    parser.add_argument("--max-batches", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--min-pending", type=int, default=0)
    args = parser.parse_args()

    cid = f"tier2-{str(uuid.uuid4())[:8]}"
    logger = HarnessLogger(tier=2, correlation_id=cid)
    mbp_active = probe_ollama_host(OLLAMA_REMOTE_HOST)
    batch_limit = args.limit or None

    logger.info(
        f"=== Tier 2 backlog worker 시작 (mbp_active={'yes' if mbp_active else 'no'}, "
        f"batch_limit={'adaptive' if batch_limit is None else batch_limit}, max_batches={args.max_batches}) ==="
    )

    current_pending = pending_count()
    if args.min_pending and current_pending < args.min_pending:
        logger.info(
            f"pending {current_pending} < min_pending {args.min_pending} — fast lane 실행 생략"
        )
        return

    # 두 도메인 모두 필터한다. (기존엔 domain 미지정 → 기본값 physical_ai만 돌아,
    #  physical_ai가 0 pending이면 매번 즉시 no-op하고 종료 → edu pending이 무한정 쌓였다.)
    domains = [d.strip() for d in os.getenv(
        "TIER2_WORKER_DOMAINS", "physical_ai,edu_consulting").split(",") if d.strip()]
    total_passed = 0
    for batch_no in range(1, args.max_batches + 1):
        before = pending_count()
        if before <= 0:
            logger.info("pending 없음 — 종료")
            break
        passed = 0
        for d in domains:
            passed += int(filter_signals(correlation_id=cid, limit=batch_limit, domain=d) or 0)
        total_passed += passed
        after = pending_count()
        logger.info(f"[batch {batch_no}] pending {before} -> {after}, passed={passed} (domains={','.join(domains)})")
        if after >= before:
            logger.info("pending 감소 없음 — 이번 실행 종료")
            break

    logger.info(f"=== Tier 2 backlog worker 종료 | total_passed={total_passed} ===")


if __name__ == "__main__":
    main()
