"""
T-07: 마케팅 티저 생성기

newsletter_issue + 상위 시그널 → X/LinkedIn/Substack Note 포맷 티저 3종 생성.
claude-haiku-4-5 사용 (저비용).
"""
import json
from typing import Optional

import anthropic

from adapters.content.refiner import get_today_cost, log_api_cost, DAILY_COST_LIMIT
from core.cost_alerts import check_and_alert
from core.database import execute_query
from core.logger import HarnessLogger

_PROMPT = """당신은 Physical AI / AGI 한국어 구독 뉴스레터 Harness의 마케터입니다.
독자층: Physical AI, 로봇, 자동화에 관심 있는 한국어 사용자 (비전문가 포함).
목적: 무료 구독자 유치, Substack 링크 클릭 유도.

아래 뉴스레터 이슈 정보를 바탕으로 3가지 플랫폼용 마케팅 카피를 생성하세요.
반드시 JSON으로만 응답하세요.

출력 스키마:
{
  "x_post": "280자 이내 한국어. 링크 제외. 핵심 훅 + 이모지 1개. 해시태그 2개 최대.",
  "linkedin_post": "400자 이내 한국어. 전문성 있는 어조. 3줄 이내.",
  "substack_note": "200자 이내 한국어. 독자 호기심 자극. 링크 클릭 유도."
}"""


def _fetch_issue_data(issue_id: int) -> dict:
    rows = execute_query(
        "SELECT id, title, free_body, published_at FROM newsletter_issues WHERE id = %s",
        (issue_id,), fetch=True,
    )
    if not rows:
        raise ValueError(f"newsletter_issues id={issue_id} 없음")
    return dict(rows[0])


def _fetch_top_signals(issue_id: int, limit: int = 3) -> list[dict]:
    issue_row = execute_query(
        "SELECT source_signal_ids FROM newsletter_issues WHERE id = %s",
        (issue_id,), fetch=True,
    )
    signal_ids = []
    if issue_row and issue_row[0].get("source_signal_ids"):
        raw = issue_row[0]["source_signal_ids"]
        if isinstance(raw, list):
            signal_ids = [int(x) for x in raw]
        elif isinstance(raw, str):
            import json
            signal_ids = [int(x) for x in json.loads(raw)]

    if signal_ids:
        placeholders = ",".join(["%s"] * len(signal_ids))
        rows = execute_query(
            f"SELECT final_title FROM refined_outputs WHERE filtered_signal_id IN ({placeholders}) LIMIT %s",
            (*signal_ids, limit), fetch=True,
        )
    else:
        rows = execute_query(
            "SELECT final_title FROM refined_outputs ORDER BY id DESC LIMIT %s",
            (limit,), fetch=True,
        )
    return [dict(r) for r in rows]


def _build_context(issue: dict, signals: list[dict]) -> str:
    titles = "\n".join(f"- {s['final_title']}" for s in signals if s.get("final_title"))
    return (
        f"이슈 번호: #{issue['id']}\n"
        f"제목: {issue.get('title') or ''}\n"
        f"요약: {(issue.get('free_body') or '')[:500]}\n\n"
        f"주요 분석 3건:\n{titles}"
    )


def generate_teasers(
    issue_id: int,
    logger: Optional[HarnessLogger] = None,
) -> dict:
    """newsletter_issue_id로 3종 티저 생성. dict 반환."""
    issue = _fetch_issue_data(issue_id)
    signals = _fetch_top_signals(issue_id)
    context = _build_context(issue, signals)

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=_PROMPT,
        messages=[{"role": "user", "content": context}],
    )

    log_api_cost("claude-haiku-4-5", resp.usage.input_tokens, resp.usage.output_tokens)
    check_and_alert(get_today_cost(logger), DAILY_COST_LIMIT, logger)

    raw = resp.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    result = json.loads(raw)

    cost = (resp.usage.input_tokens / 1000 * 0.0008 +
            resp.usage.output_tokens / 1000 * 0.004)
    if logger:
        logger.info(f"티저 생성 완료 (issue_id={issue_id}, cost=${cost:.5f})")

    return result
