"""
T-11: 부대표 콘텐츠 검토 카드 — Slack 기반

SLACK_CHANNEL_VP_MARKET_READ에 검토 요청 카드 게시.
부대표가 특정 키워드로 답장하면 content_reviews 테이블에 기록.

답장 형식:
  OK             → recommendation='ready'
  수정: <메모>    → recommendation='revise', jargon_notes=메모
  보류            → recommendation='hold'
"""
import json
from typing import Optional

from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.slack_router import send_slack_route


_REVIEW_PENDING_KEY = "vp_review_pending"


def request_vp_review(
    issue_id: int,
    logger: Optional[HarnessLogger] = None,
) -> bool:
    """부대표에게 Slack 검토 요청 카드 발송. 발송 성공 시 True."""
    rows = execute_query(
        "SELECT id, title, free_body FROM newsletter_issues WHERE id = %s",
        (issue_id,), fetch=True,
    )
    if not rows:
        if logger:
            logger.error(f"newsletter_issues id={issue_id} 없음")
        return False

    issue = rows[0]
    title = issue.get("title") or f"이슈 #{issue_id}"
    preview = (issue.get("free_body") or "")[:300]

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📝 콘텐츠 검토 요청 — 이슈 #{issue_id}"},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*제목*\n{title}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*본문 미리보기*\n{preview}..."},
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*검토 후 아래 중 하나로 답장해주세요:*\n"
                    "✅ `OK` — 발행 가능\n"
                    "🔁 `수정: <어색한 표현이나 메모>` — 수정 후 재검토\n"
                    "⏸ `보류` — 이번 이슈 발행 보류\n\n"
                    f"_이슈 ID: {issue_id}_"
                ),
            },
        },
    ]

    try:
        send_slack_route("vp_market_read", {
            "text": f"[검토 요청] {title}",
            "blocks": blocks,
        })
        execute_query(
            """INSERT INTO ceo_decisions
                   (target_type, target_id, decision, approval_type, reason, decided_by)
               VALUES ('newsletter_issue', %s, 'hold', 'vice_president_review_request',
                       'VP 검토 요청 발송', 'vp_review_agent')""",
            (issue_id,),
        )
        if logger:
            logger.info(f"[vp_review] 검토 요청 발송: issue_id={issue_id}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"[vp_review] 발송 실패: {e}")
        return False


def parse_vp_response(text: str, issue_id: int, reviewer_slack_id: str) -> Optional[dict]:
    """
    부대표 Slack 답장 파싱 → content_reviews INSERT.
    Returns inserted row dict or None if not a review response.
    """
    t = text.strip()
    recommendation = None
    jargon_notes = ""

    if t.lower() in ("ok", "ok!", "발행ok", "발행 ok"):
        recommendation = "ready"
    elif t.startswith("수정:") or t.startswith("수정 :"):
        recommendation = "revise"
        jargon_notes = t.split(":", 1)[1].strip() if ":" in t else ""
    elif t in ("보류", "보류.", "hold"):
        recommendation = "hold"

    if recommendation is None:
        return None

    result = execute_query(
        """INSERT INTO content_reviews
               (newsletter_issue_id, reviewer_role, readability, shareability,
                jargon_notes, recommendation)
           VALUES (%s, 'vice_president', 'reviewed', 'reviewed', %s, %s)
           RETURNING id""",
        (issue_id, jargon_notes, recommendation),
        fetch=True,
    )
    row_id = result[0]["id"] if result else None

    if recommendation == "ready":
        execute_query(
            """INSERT INTO ceo_decisions
                   (target_type, target_id, decision, approval_type, reason, decided_by)
               VALUES ('newsletter_issue', %s, 'approved', 'vice_president_review_request',
                       'VP 검토 완료: ready', %s)""",
            (issue_id, f"slack:{reviewer_slack_id}"),
        )

    return {"id": row_id, "recommendation": recommendation, "jargon_notes": jargon_notes}


def check_vp_review_approved(issue_id: int) -> bool:
    """발행 전 VP 검토 완료(ready) 여부 확인."""
    rows = execute_query(
        """SELECT id FROM content_reviews
           WHERE newsletter_issue_id = %s AND recommendation = 'ready'
           ORDER BY id DESC LIMIT 1""",
        (issue_id,), fetch=True,
    )
    return bool(rows)
