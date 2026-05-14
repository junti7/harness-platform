"""
T-13: DLQ 자동 재시도 스크립트

사용법:
  python scripts/retry_dlq.py          # 재시도 대상 자동 처리
  python scripts/retry_dlq.py --dry-run

자동화:
  Mac Mini LaunchAgent: 6시간마다
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import anthropic

from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.refiner import refine_signal, log_api_cost, DAILY_COST_LIMIT, get_today_cost
from core.cost_alerts import check_and_alert
from adapters.content.slack_router import send_slack_route

MAX_RETRIES = 3


def get_retryable_entries(logger: HarnessLogger) -> list[dict]:
    return execute_query(
        """SELECT id, tier, item_id, item_type, error_message, raw_data, retry_count
           FROM dead_letter_queue
           WHERE resolved = FALSE
             AND retry_count < %s
             AND created_at < NOW() - INTERVAL '1 hour'
           ORDER BY retry_count ASC, created_at ASC
           LIMIT 20""",
        (MAX_RETRIES,), fetch=True,
    )


def _increment_retry(dlq_id: int) -> None:
    execute_query(
        "UPDATE dead_letter_queue SET retry_count = retry_count + 1, last_retry_at = NOW() WHERE id = %s",
        (dlq_id,),
    )


def _mark_resolved(dlq_id: int) -> None:
    execute_query(
        "UPDATE dead_letter_queue SET resolved = TRUE, last_retry_at = NOW() WHERE id = %s",
        (dlq_id,),
    )


def _mark_permanently_failed(dlq_id: int, logger: HarnessLogger) -> None:
    execute_query(
        "UPDATE dead_letter_queue SET resolved = TRUE, last_retry_at = NOW() WHERE id = %s",
        (dlq_id,),
    )
    try:
        send_slack_route("ops_incidents", {
            "text": f":octagonal_sign: DLQ 영구 실패: id={dlq_id} — 수동 검토 필요",
        })
    except Exception as e:
        logger.warning(f"DLQ 실패 알림 전송 오류: {e}")


def retry_tier3_signal(entry: dict, client: anthropic.Anthropic, dry_run: bool, logger: HarnessLogger) -> bool:
    raw_data = entry.get("raw_data")
    if isinstance(raw_data, str):
        try:
            row = json.loads(raw_data)
        except json.JSONDecodeError:
            logger.error(f"raw_data JSON 파싱 실패: dlq_id={entry['id']}")
            return False
    else:
        row = raw_data or {}

    if not row.get("id"):
        return False

    try:
        result = refine_signal(client, row)
        check_and_alert(get_today_cost(logger), DAILY_COST_LIMIT, logger)

        if not dry_run:
            execute_query(
                """INSERT INTO refined_outputs
                       (filtered_signal_id, final_title, final_body, tags, tier3_model)
                   VALUES (%s, %s, %s, %s, %s)""",
                (
                    row["id"],
                    result.get("final_title", ""),
                    json.dumps(result, ensure_ascii=False),
                    json.dumps(result.get("tags", []), ensure_ascii=False),
                    "claude-sonnet-4-6",
                ),
            )
        logger.info(f"  재시도 성공: dlq_id={entry['id']} signal={row['id']}")
        return True
    except Exception as e:
        logger.warning(f"  재시도 실패: dlq_id={entry['id']}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="DLQ 자동 재시도")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logger = HarnessLogger(tier=3, correlation_id="dlq-retry")
    logger.info("=== DLQ 재시도 시작 ===")

    entries = get_retryable_entries(logger)
    if not entries:
        logger.info("재시도 대상 없음")
        return

    logger.info(f"재시도 대상: {len(entries)}개")
    client = anthropic.Anthropic()
    resolved = failed_perm = 0

    for entry in entries:
        dlq_id = entry["id"]
        retry_count = entry.get("retry_count", 0)
        item_type = entry.get("item_type", "")

        logger.info(f"[{retry_count + 1}/{MAX_RETRIES}] dlq_id={dlq_id} type={item_type}")

        if get_today_cost(logger) >= DAILY_COST_LIMIT:
            logger.warning("일일 비용 한도 도달 — DLQ 재시도 중단")
            break

        success = False
        if item_type == "filtered_signal":
            success = retry_tier3_signal(entry, client, args.dry_run, logger)

        if not dry_run := args.dry_run:
            if success:
                _mark_resolved(dlq_id)
                resolved += 1
            else:
                _increment_retry(dlq_id)
                if retry_count + 1 >= MAX_RETRIES:
                    _mark_permanently_failed(dlq_id, logger)
                    failed_perm += 1
        else:
            logger.info(f"  [dry-run] 결과: {'성공' if success else '실패'}")

    tag = "[dry-run] " if args.dry_run else ""
    logger.info(f"=== {tag}DLQ 완료: 해결 {resolved}개 / 영구실패 {failed_perm}개 ===")


if __name__ == "__main__":
    main()
