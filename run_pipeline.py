import sys
import time
from core.logger import HarnessLogger

def run():
    logger = HarnessLogger(tier=0)
    start = time.time()
    logger.info("=" * 60)
    logger.info("Harness 파이프라인 시작")
    logger.info("=" * 60)

    results = {}

    # Tier 1
    logger.info("[Tier 1] 수집 시작")
    try:
        from adapters.content.collector import collect
        results["tier1"] = collect()
        logger.info(f"[Tier 1] 완료: {results['tier1']}건 수집")
    except Exception as e:
        logger.error(f"[Tier 1] 실패: {e}")
        sys.exit(1)

    # Tier 2
    logger.info("[Tier 2] 필터링 시작")
    try:
        from adapters.content.filter import filter_signals
        results["tier2"] = filter_signals()
        logger.info(f"[Tier 2] 완료: {results['tier2']}건 통과")
    except Exception as e:
        logger.error(f"[Tier 2] 실패: {e}")
        sys.exit(1)

    # Tier 3
    logger.info("[Tier 3] 정제 시작")
    try:
        from adapters.content.refiner import refine
        results["tier3"] = refine()
        logger.info(f"[Tier 3] 완료: {results['tier3']}건 정제")
    except Exception as e:
        logger.error(f"[Tier 3] 실패: {e}")
        sys.exit(1)

    # Tier 4
    logger.info("[Tier 4] 발행 시작")
    try:
        from adapters.content.publisher import publish
        results["tier4"] = publish()
        logger.info(f"[Tier 4] 완료: {results['tier4']}건 발행")
    except Exception as e:
        logger.error(f"[Tier 4] 실패: {e}")
        sys.exit(1)

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info(
        f"파이프라인 완료 ({elapsed:.1f}s) | "
        f"수집 {results['tier1']} → 필터 {results['tier2']} → "
        f"정제 {results['tier3']} → 발행 {results['tier4']}"
    )
    logger.info("=" * 60)

if __name__ == "__main__":
    run()
