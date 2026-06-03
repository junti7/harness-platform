import sys
import time
import uuid
import os
import logging
from pathlib import Path

# load .env from repo root before importing any module that calls load_dotenv()
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path, override=True)

from adapters.content.slack_router import send_slack_route
from core.logger import HarnessLogger
from core.database import execute_query
from scripts.system_integrity_check import run_check as run_system_integrity_check


def _save_run_start(cid: str) -> int:
    result = execute_query(
        "INSERT INTO pipeline_runs (correlation_id) VALUES (%s) RETURNING id",
        (cid,), fetch=True
    )
    return result[0]["id"] if result else None


def _truncate_error(error: str, limit: int = 500) -> str:
    text = (error or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


def _parse_failure(error: str) -> tuple[str, str]:
    raw_error = error or "unknown"
    if ":" not in raw_error:
        return "?", raw_error

    tier_label, detail = raw_error.split(":", 1)
    tier = tier_label.replace("tier", "").strip() or "?"
    return tier, detail.strip()


def _notify_on_failure(run_id: int, correlation_id: str, error: str) -> None:
    tier, detail = _parse_failure(error)
    truncated_error = _truncate_error(detail)
    text = (
        f":fire: *[파이프라인 장애]* Tier {tier} 실패\n"
        f"오류: `{truncated_error}`\n"
        f"correlation_id: `{correlation_id}` | run_id: `{run_id or 'n/a'}`"
    )
    payload = {
        "text": text,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"correlation_id=`{correlation_id}`"},
                    {"type": "mrkdwn", "text": f"pipeline_runs.id=`{run_id or 'n/a'}`"},
                ],
            },
        ],
    }
    # ops 채널 + CEO 채널 동시 발송
    send_slack_route("ops_incidents", payload)
    send_slack_route("exec_president_decisions", payload)


def _save_run_end(run_id: int, results: dict, status: str, error: str = None):
    if run_id:
        try:
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
        except Exception as exc:
            logging.getLogger("harness.pipeline").warning(
                "pipeline_runs 종료 기록 실패: %s", exc
            )

    if status == "failed":
        correlation_id = results.get("correlation_id", "unknown")
        try:
            _notify_on_failure(run_id, correlation_id, error or "unknown")
        except Exception as exc:
            logging.getLogger("harness.pipeline").warning(
                "Slack failure alert 전송 실패: %s", exc
            )


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

    results = {"correlation_id": pipeline_cid}

    logger.info("[Preflight] 시스템 무결성 점검 시작")
    preflight = run_system_integrity_check()
    if not preflight["ok"]:
        error = f"preflight:{'; '.join(preflight['findings'])}"
        logger.error(f"[Preflight] 실패: {error}")
        _save_run_end(run_id, results, "failed", error)
        sys.exit(1)
    logger.info("[Preflight] 통과")

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
        t2_physical = filter_signals(correlation_id=pipeline_cid, domain="physical_ai")
        logger.info(f"[Tier 2] physical_ai: {t2_physical}건 통과")
        t2_edu = filter_signals(correlation_id=pipeline_cid, domain="edu_consulting")
        logger.info(f"[Tier 2] edu_consulting: {t2_edu}건 통과")
        results["tier2"] = t2_physical + t2_edu

        from adapters.content.signalizer import promote_signals
        results["signals"] = promote_signals(correlation_id=pipeline_cid)
        logger.info(f"[Tier 2] Signal 승격 완료: {results['signals']}건")
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

    # QA — qa_clear 없는 refined_outputs 자동 검사
    logger.info("[QA] 자동 QA 검사 시작")
    try:
        from adapters.content.qa_agent import qa_check_refined_output
        pending_qa = execute_query("""
            SELECT ro.id FROM refined_outputs ro
            WHERE NOT EXISTS (
                SELECT 1 FROM ceo_decisions cd
                WHERE cd.target_type = 'refined_output'
                  AND cd.target_id = ro.id
                  AND cd.approval_type = 'qa_clear'
            )
            ORDER BY ro.created_at DESC
            LIMIT 50
        """, fetch=True) or []

        qa_passed = 0
        qa_failed = 0
        for qrow in pending_qa:
            ok = qa_check_refined_output(qrow["id"], correlation_id=pipeline_cid)
            if ok:
                qa_passed += 1
            else:
                qa_failed += 1

        results["qa_passed"] = qa_passed
        results["qa_failed"] = qa_failed
        logger.info(f"[QA] 완료: 통과 {qa_passed}건 / 탈락 {qa_failed}건 (대상 {len(pending_qa)}건)")
    except Exception as e:
        logger.warning(f"[QA] 자동 QA 실패 (비치명적, 발행 계속): {e}")

    # Tier 4
    logger.info("[Tier 4] 발행 시작")
    try:
        from adapters.content.publisher import publish
        results["tier4"] = publish(correlation_id=pipeline_cid)
        logger.info(f"[Tier 4] 완료: {results['tier4']}건 발행")

        if os.getenv("MOBILE_BRIEFING_ENABLED", "false").lower() == "true":
            from adapters.content.daily_briefing import send_daily_mobile_briefing
            briefing = send_daily_mobile_briefing(correlation_id=pipeline_cid)
            results["mobile_briefing"] = briefing.get("sent", 0)
            logger.info(f"[Tier 4] 모바일 브리핑 완료: {results['mobile_briefing']}건")
    except Exception as e:
        logger.error(f"[Tier 4] 실패: {e}")
        _save_run_end(run_id, results, "failed", f"tier4:{e}")
        sys.exit(1)

    # 교육 상담사 근거 뱅크 갱신 — 최신 edu_consulting 정제 결과를 상담 대화에 반영
    # (실패해도 파이프라인 성공에 영향 주지 않음 — 비치명적)
    try:
        from scripts.refresh_edu_evidence_bank import build_bank, BANK_PATH
        import json as _json
        bank = build_bank(window_days=45, max_fresh=25)
        if bank["_meta"]["counts"]["total"] > 0:
            BANK_PATH.write_text(_json.dumps(bank, ensure_ascii=False, indent=2), encoding="utf-8")
            c = bank["_meta"]["counts"]
            logger.info(f"[근거 뱅크] 갱신 완료: 총 {c['total']} (앵커 {c['evergreen_anchors']} + 최신 {c['fresh_pipeline']})")
    except Exception as e:
        logger.warning(f"[근거 뱅크] 갱신 실패 (비치명적): {e}")

    # 교육 RAG 인덱스 증분 갱신 — 오늘 새로 정제된 항목만 임베딩해 검색 코퍼스에 stack.
    # 매일 누적되어 RAG가 갈수록 두꺼워진다(상담 근거 품질 상승). 비치명적.
    try:
        from scripts.build_edu_evidence_index import build, INDEX_PATH
        import json as _json
        index = build(rebuild=False)
        INDEX_PATH.write_text(_json.dumps(index, ensure_ascii=False), encoding="utf-8")
        logger.info(f"[RAG 인덱스] 증분 갱신 완료: 총 {index['count']}건")
    except Exception as e:
        logger.warning(f"[RAG 인덱스] 갱신 실패 (비치명적): {e}")

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
    import argparse
    parser = argparse.ArgumentParser(description="Harness 파이프라인 실행")
    parser.add_argument(
        "--tier", type=int, default=None,
        help="특정 Tier만 실행 (예: --tier 3). 생략 시 전체 실행."
    )
    args, _ = parser.parse_known_args()

    if args.tier == 3:
        from dotenv import load_dotenv as _ld
        _ld(_env_path, override=True)
        from adapters.content.refiner import refine
        import uuid as _uuid
        cid = str(_uuid.uuid4())[:8]
        logger = HarnessLogger(tier=3, correlation_id=cid)
        logger.info(f"=== Tier 3 단독 실행 (run_id={cid}) ===")
        count = refine(correlation_id=cid)
        logger.info(f"=== Tier 3 완료: {count}건 ===")
    else:
        run()
