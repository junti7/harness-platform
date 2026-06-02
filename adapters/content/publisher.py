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


def has_ceo_approval(target_type: str, target_id: int) -> bool:
    result = execute_query("""
        SELECT decision
        FROM ceo_decisions
        WHERE target_type = %s AND target_id = %s
          AND approval_type = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (target_type, target_id, "report_publish_approve"), fetch=True)
    return bool(result and result[0]["decision"] == "approved")


def has_required_approval(target_type: str, target_id: int, approval_type: str) -> bool:
    result = execute_query("""
        SELECT decision
        FROM ceo_decisions
        WHERE target_type = %s AND target_id = %s
          AND approval_type = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (target_type, target_id, approval_type), fetch=True)
    return bool(result and result[0]["decision"] == "approved")


def needs_ceo_approval(row: dict) -> bool:
    sensitivity = (row.get("sensitivity_level") or "low").lower()
    return bool(row.get("requires_ceo_approval") or sensitivity in {"high", "critical"})


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


def _extract_summary(body_raw) -> str:
    try:
        body = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
        hook = body.get("hook") or ""
        if hook:
            return hook[:500]
        deep = body.get("deep_analysis") or {}
        if isinstance(deep, dict):
            return (deep.get("technical_breakdown") or "")[:500]
    except Exception:
        pass
    return str(body_raw)[:500]


def _historical_value(score) -> str:
    try:
        s = float(score)
        if s >= 0.9:
            return "high"
        if s >= 0.7:
            return "medium"
    except (TypeError, ValueError):
        pass
    return "low"


_DOMAIN_PROJECT: dict[str, str] = {
    "physical_ai": "Physical AI Weekly",
    "edu_consulting": "AI 교육 컨설팅",
}
_DOMAIN_TEAM: dict[str, list[str]] = {
    "physical_ai": ["Engineering", "QA"],
    "edu_consulting": ["교육컨설팅", "QA"],
}


def _build_notion_payload(row: dict, artifact_type: str = "refined_output") -> dict:
    tags = _parse_tags(row.get("tags") or [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = row.get("final_title") or row.get("title") or "Untitled Harness Artifact"
    body_raw = row.get("final_body") or row.get("summary") or row.get("body") or ""
    source = row.get("source") or artifact_type
    row_id = row.get("id")
    score = row.get("score")
    domain = row.get("domain") or "physical_ai"
    project_name = _DOMAIN_PROJECT.get(domain, "Physical AI Weekly")
    team_names = _DOMAIN_TEAM.get(domain, ["Engineering", "QA"])

    properties = {
        "제목": {"title": [{"text": {"content": title[:2000]}}]},
        "본문": {"rich_text": [{"text": {"content": str(body_raw)[:2000]}}]},
        "태그": {"multi_select": [{"name": t[:100]} for t in tags[:5]]},
        "소스": {"rich_text": [{"text": {"content": source[:500]}}]},
        "발행일": {"date": {"start": today}},
        "Artifact Type": {"select": {"name": "issue_archive" if artifact_type == "refined_output" else "research_report"}},
        "Team": {"multi_select": [{"name": t} for t in team_names]},
        "Source Channel": {"select": {"name": "db"}},
        "Event Date": {"date": {"start": today}},
        "LLM Ready": {"checkbox": True},
        "Historical Value": {"select": {"name": _historical_value(score)}},
        "Confidentiality": {"select": {"name": "internal"}},
        "Project": {"rich_text": [{"text": {"content": project_name}}]},
        "Domain": {"select": {"name": domain}},
        "Project Status": {"select": {"name": "done"}},
        "Outcome": {"select": {"name": "success"}},
    }

    if row_id:
        properties["Canonical Key"] = {"rich_text": [{"text": {"content": f"{artifact_type}-{row_id}"}}]}
        properties["DB Record Ref"] = {"rich_text": [{"text": {"content": f"{artifact_type}s.id={row_id}"}}]}

    summary = _extract_summary(body_raw)
    if summary:
        properties["Summary"] = {"rich_text": [{"text": {"content": summary}}]}

    return {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": properties,
    }


def publish_notion(row: dict, logger: HarnessLogger, artifact_type: str = "refined_output") -> str:
    payload = _build_notion_payload(row, artifact_type=artifact_type)

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


def mark_published(row_id: int, notion_page_id: str | None = None):
    execute_query("""
        UPDATE refined_outputs
        SET published = TRUE, notion_page_id = %s, published_at = NOW()
        WHERE id = %s
    """, (notion_page_id, row_id))


def mark_report_published(row_id: int, notion_page_id: str | None = None):
    execute_query("""
        UPDATE research_reports
        SET published = TRUE, notion_page_id = %s, published_at = NOW(), updated_at = NOW()
        WHERE id = %s
    """, (notion_page_id, row_id))


def save_to_dlq(row: dict, error: str, logger: HarnessLogger):
    try:
        item_type = row.get("item_type") or "refined_output"
        execute_query("""
            INSERT INTO dead_letter_queue (tier, item_id, item_type, error_message, raw_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            4,
            row["id"],
            item_type,
            str(error)[:500],
            json.dumps({k: str(v) for k, v in row.items()}, ensure_ascii=False),
        ))
    except Exception as dlq_err:
        logger.error(f"  → DLQ 저장 실패: {dlq_err}")


def get_unpublished() -> list:
    return execute_query("""
        SELECT
            ro.id, ro.final_title, ro.final_body, ro.tags,
            ro.sensitivity_level, ro.requires_ceo_approval,
            fs.content_hash, fs.source, fs.score, fs.category,
            COALESCE(fs.domain, 'physical_ai') AS domain
        FROM refined_outputs ro
        JOIN filtered_signals fs ON ro.filtered_signal_id = fs.id
        WHERE ro.published = FALSE
        ORDER BY fs.score DESC
    """, fetch=True)


def get_unpublished_research_reports() -> list:
    return execute_query("""
        SELECT
            id, title, report_type, audience, body, summary,
            sensitivity_level, requires_ceo_approval, status,
            source_signal_ids, cost_usd
        FROM research_reports
        WHERE published = FALSE
          AND status IN ('final', 'approved', 'publish_ready')
        ORDER BY updated_at DESC, created_at DESC
    """, fetch=True)


def _publish_refined_outputs(logger: HarnessLogger) -> tuple[int, int, int, list[dict]]:
    rows = get_unpublished()
    if not rows:
        logger.info("발행할 refined_outputs 없음")
        return 0, 0, 0, []

    logger.info(f"refined_outputs 발행 대상: {len(rows)}개")

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

        if not has_required_approval("refined_output", row["id"], "qa_clear"):
            logger.warning("  → QA clear 없음 — 발행 보류")
            skipped += 1
            continue

        if needs_ceo_approval(row) and not has_ceo_approval("refined_output", row["id"]):
            logger.warning("  → 고민감 항목 CEO 승인 없음 — 발행 보류")
            skipped += 1
            continue

        if is_already_published(row["content_hash"]):
            logger.info("  → 중복 발행 차단 (content_hash 일치) — 스킵")
            skipped += 1
            continue

        try:
            page_id = publish_notion(row, logger, artifact_type="refined_output")
            mark_published(row["id"], page_id)
            published_items.append(row)
            logger.info(f"  → Notion 완료: page_id={page_id}")
            published += 1
        except Exception as e:
            logger.error(f"  → {MAX_RETRIES}회 재시도 후 최종 실패: {e}")
            save_to_dlq(row, str(e), logger)
            failed += 1

    return published, skipped, failed, published_items


def _publish_research_reports(logger: HarnessLogger) -> tuple[int, int, int, list[dict]]:
    rows = get_unpublished_research_reports()
    if not rows:
        logger.info("발행할 research_reports 없음")
        return 0, 0, 0, []

    logger.info(f"research_reports Notion 저장 대상: {len(rows)}개")

    published_items = []
    published = 0
    skipped = 0
    failed = 0

    for i, row in enumerate(rows):
        row = dict(row)
        logger.info(f"[report {i + 1}/{len(rows)}] {row['title'][:50]}...")

        if not has_required_approval("research_report", row["id"], "qa_clear"):
            logger.warning("  → QA clear 없음 — Notion 저장 보류")
            skipped += 1
            continue

        if needs_ceo_approval(row) and not has_ceo_approval("research_report", row["id"]):
            logger.warning("  → 고민감 report 대표 승인 없음 — Notion 저장 보류")
            skipped += 1
            continue

        try:
            page_id = publish_notion(row, logger, artifact_type=f"research_report:{row.get('report_type')}")
            mark_report_published(row["id"], page_id)
            published_items.append({
                "final_title": row["title"],
                "final_body": row.get("summary") or row.get("body") or "",
                "tags": [row.get("report_type") or "research_report", row.get("audience") or "internal"],
            })
            logger.info(f"  → Research report Notion 완료: page_id={page_id}")
            published += 1
        except Exception as e:
            logger.error(f"  → Research report Notion 최종 실패: {e}")
            save_to_dlq({**row, "id": row["id"], "item_type": "research_report"}, str(e), logger)
            failed += 1

    return published, skipped, failed, published_items


def publish(correlation_id: str = None):
    logger = HarnessLogger(tier=4, correlation_id=correlation_id)
    logger.info("=== Tier 4 발행 시작 ===")

    if not NOTION_API_KEY:
        logger.error("NOTION_API_KEY 미설정 — 중단")
        return 0

    if not NOTION_DATABASE_ID:
        logger.error("NOTION_DATABASE_ID 미설정 — 중단")
        return 0

    refined_published, refined_skipped, refined_failed, refined_items = _publish_refined_outputs(logger)
    report_published, report_skipped, report_failed, report_items = _publish_research_reports(logger)

    published_items = refined_items + report_items
    published = refined_published + report_published
    skipped = refined_skipped + report_skipped
    failed = refined_failed + report_failed

    if published_items:
        publish_slack(published_items, logger)
    elif published == 0 and skipped == 0 and failed == 0:
        publish_slack([], logger)

    logger.info("=" * 50)
    logger.info(f"Tier 4 완료: Notion 저장 {published}개 / 스킵 {skipped}개 / 실패 {failed}개")
    logger.info("=" * 50)
    return published


if __name__ == "__main__":
    publish()
