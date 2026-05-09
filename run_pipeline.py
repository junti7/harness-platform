import sys
import time
import uuid
from core.logger import HarnessLogger
from core.database import execute_query


def _save_run_start(cid: str) -> int:
    result = execute_query(
        "INSERT INTO pipeline_runs (correlation_id) VALUES (%s) RETURNING id",
        (cid,), fetch=True
    )
    return result[0]["id"] if result else None


def _save_run_end(run_id: int, results: dict, status: str, error: str = None):
    if not run_id:
        return
    execute_query("""
        UPDATE pipeline_runs
        SET finished_at = NOW(),
            tier1_count = %s, tier2_count = %s,
            tier3_count = %s, tier4_count = %s,
            status = %s, error = %s
        WHERE id = %s
    """, (
        results.get("tier1"), results.get("tier2"),
        results.get("tier3"), results.get("tier4"),
        status, error, run_id,
    ))


def run():
    pipeline_cid = str(uuid.uuid4())[:8]
    logger = HarnessLogger(tier=0, correlation_id=pipeline_cid)
    start = time.time()

    logger.info("=" * 60)
    logger.info(f"Harness 파이프라인 시작 (run_id={pipeline_cid})")
    logger.info("=" * 60)

    run_id = None
    try:
        run_id = _save_run_start(pipeline_cid)
    except Exception as e:
        logger.warning(f"pipeline_runs 기록 실패 (비치명적): {e}")

    results = {}

    # Tier 1
    logger.info("[Tier 1] 수집 시작")
    try:
        from adapters.content.collector import collect
        results["tier1"] = collect(correlation_id=pipeline_cid)
        logger.info(f"[Tier 1] 완료: {results['tier1']}건 수집")
    except Exception as e:
        logger.error(f"[Tier 1] 실패: {e}")
        _save_run_end(run_id, results, "failed", f"tier1:{e}")
        sys.exit(1)

    # Tier 2
    logger.info("[Tier 2] 필터링 시작")
    try:
        from adapters.content.filter import filter_signals
        results["tier2"] = filter_signals(correlation_id=pipeline_cid)
        logger.info(f"[Tier 2] 완료: {results['tier2']}건 통과")
    except Exception as e:
        logger.error(f"[Tier 2] 실패: {e}")
        _save_run_end(run_id, results, "failed", f"tier2:{e}")
        sys.exit(1)

    # Tier 3
    logger.info("[Tier 3] 정제 시작")
    try:
        from adapters.content.refiner import refine
        results["tier3"] = refine(correlation_id=pipeline_cid)
        logger.info(f"[Tier 3] 완료: {results['tier3']}건 정제")
    except Exception as e:
        logger.error(f"[Tier 3] 실패: {e}")
        _save_run_end(run_id, results, "failed", f"tier3:{e}")
        sys.exit(1)

    # Tier 4
    logger.info("[Tier 4] 발행 시작")
    try:
        from adapters.content.publisher import publish
        results["tier4"] = publish(correlation_id=pipeline_cid)
        logger.info(f"[Tier 4] 완료: {results['tier4']}건 발행")
    except Exception as e:
        logger.error(f"[Tier 4] 실패: {e}")
        _save_run_end(run_id, results, "failed", f"tier4:{e}")
        sys.exit(1)

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info(
        f"파이프라인 완료 ({elapsed:.1f}s) | "
        f"수집 {results['tier1']} → 필터 {results['tier2']} → "
        f"정제 {results['tier3']} → 발행 {results['tier4']}"
    )
    logger.info("=" * 60)

    _save_run_end(run_id, results, "success")


if __name__ == "__main__":
    run()
