import json
import os
import time
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv
from core.database import execute_query
from core.logger import HarnessLogger

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
# .env의 DB ID는 "id?v=view_id" 형태일 수 있어서 파싱
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").split("?")[0]
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
NOTION_VERSION = "2022-06-28"
MAX_RETRIES = 3


def sanity_check(row: dict) -> bool:
    for field in ("final_title", "final_body", "tags"):
        if not row.get(field):
            return False
    return True


def is_already_published(content_hash: str) -> bool:
    result = execute_query("""
        SELECT 1 FROM refined_outputs ro
        JOIN filtered_signals fs ON ro.filtered_signal_id = fs.id
        WHERE fs.content_hash = %s AND ro.published = TRUE
        LIMIT 1
    """, (content_hash,), fetch=True)
    return bool(result)


def _parse_tags(tags) -> list[str]:
    if isinstance(tags, str):
        return json.loads(tags)
    return tags or []


def _notion_headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _build_notion_payload(row: dict) -> dict:
    tags = _parse_tags(row["tags"])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "제목": {
                "title": [{"text": {"content": row["final_title"][:2000]}}]
            },
            "본문": {
                "rich_text": [{"text": {"content": row["final_body"][:2000]}}]
            },
            "태그": {
                "multi_select": [{"name": t[:100]} for t in tags[:5]]
            },
            "소스": {
                "rich_text": [{"text": {"content": row.get("source", "")[:500]}}]
            },
            "발행일": {
                "date": {"start": today}
            },
        }
    }


def publish_notion(row: dict, logger: HarnessLogger) -> str:
    payload = _build_notion_payload(row)

    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.post(
                "https://api.notion.com/v1/pages",
                headers=_notion_headers(),
                json=payload,
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()["id"]
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                logger.warning(f"  → Notion 재시도 {attempt + 1}/{MAX_RETRIES}: {e} ({wait}s 대기)")
                time.sleep(wait)
            else:
                raise


def publish_slack(items: list[dict], logger: HarnessLogger):
    if not SLACK_WEBHOOK_URL or SLACK_WEBHOOK_URL == "your_webhook_here":
        logger.warning("Slack Webhook URL 미설정 — 슬랙 발송 스킵")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    if not items:
        text = f"*[Harness Daily Digest]* {today} — 오늘의 새 기사가 없습니다."
    else:
        lines = [f"*[Harness Daily Digest]* {today} — {len(items)}건\n"]
        for i, item in enumerate(items, 1):
            tags = _parse_tags(item["tags"])
            tag_str = " ".join(f"`{t}`" for t in tags[:3])
            body_preview = item["final_body"][:150]
            if len(item["final_body"]) > 150:
                body_preview += "..."
            lines.append(f"{i}. *{item['final_title']}*\n{tag_str}\n{body_preview}\n")
        text = "\n".join(lines)

    for attempt in range(MAX_RETRIES):
        try:
            resp = httpx.post(
                SLACK_WEBHOOK_URL,
                json={"text": text},
                timeout=10.0,
            )
            resp.raise_for_status()
            logger.info(f"  → Slack 발송 완료 ({len(items)}건)")
            return

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                logger.warning(f"  → Slack 재시도 {attempt + 1}/{MAX_RETRIES}: {e} ({wait}s 대기)")
                time.sleep(wait)
            else:
                logger.error(f"  → Slack 최종 실패 (비치명적): {e}")
                return  # Slack 실패는 Notion 발행을 롤백하지 않음


def mark_published(row_id: int):
    execute_query("""
        UPDATE refined_outputs
        SET published = TRUE, published_at = NOW()
        WHERE id = %s
    """, (row_id,))


def save_to_dlq(row: dict, error: str, logger: HarnessLogger):
    try:
        execute_query("""
            INSERT INTO dead_letter_queue (tier, item_id, item_type, error_message, raw_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            4,
            row["id"],
            "refined_output",
            str(error)[:500],
            json.dumps({k: str(v) for k, v in row.items()}, ensure_ascii=False),
        ))
    except Exception as dlq_err:
        logger.error(f"  → DLQ 저장 실패: {dlq_err}")


def get_unpublished() -> list:
    return execute_query("""
        SELECT
            ro.id, ro.final_title, ro.final_body, ro.tags,
            fs.content_hash, fs.source, fs.score, fs.category
        FROM refined_outputs ro
        JOIN filtered_signals fs ON ro.filtered_signal_id = fs.id
        WHERE ro.published = FALSE
        ORDER BY fs.score DESC
    """, fetch=True)


def publish():
    logger = HarnessLogger(tier=4)
    logger.info("=== Tier 4 발행 시작 ===")

    if not NOTION_API_KEY:
        logger.error("NOTION_API_KEY 미설정 — 중단")
        return 0

    if not NOTION_DATABASE_ID:
        logger.error("NOTION_DATABASE_ID 미설정 — 중단")
        return 0

    rows = get_unpublished()
    if not rows:
        logger.info("발행할 데이터 없음")
        publish_slack([], logger)
        return 0

    logger.info(f"발행 대상: {len(rows)}개")

    published_items = []
    published = 0
    skipped = 0
    failed = 0

    for i, row in enumerate(rows):
        row = dict(row)
        logger.info(f"[{i + 1}/{len(rows)}] {row['final_title'][:50]}...")

        if not sanity_check(row):
            logger.warning("  → Sanity Check 실패: 필수 필드 누락 — 탈락")
            skipped += 1
            continue

        if is_already_published(row["content_hash"]):
            logger.info("  → 중복 발행 차단 (content_hash 일치) — 스킵")
            skipped += 1
            continue

        try:
            page_id = publish_notion(row, logger)
            mark_published(row["id"])
            published_items.append(row)
            logger.info(f"  → Notion 완료: page_id={page_id}")
            published += 1
        except Exception as e:
            logger.error(f"  → {MAX_RETRIES}회 재시도 후 최종 실패: {e}")
            save_to_dlq(row, str(e), logger)
            failed += 1

    if published_items:
        publish_slack(published_items, logger)

    logger.info("=" * 50)
    logger.info(f"Tier 4 완료: 발행 {published}개 / 스킵 {skipped}개 / 실패 {failed}개")
    logger.info("=" * 50)
    return published


if __name__ == "__main__":
    publish()
