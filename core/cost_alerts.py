"""
T-08: Claude API 일일 비용 임계점 Slack 알림

임계점: 50% / 90% / 100% of DAILY_COST_LIMIT_USD
- 이미 발송된 임계점은 당일 재발송 안 함 (idempotent)
- SLACK_CHANNEL_EXEC_DAILY_BRIEF 채널로 전송
"""
import os
from datetime import date

from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.slack_router import send_slack_route

THRESHOLDS = [0.50, 0.90, 1.00]


def check_and_alert(today_cost: float, limit: float, logger: HarnessLogger | None = None) -> list[float]:
    """오늘 비용 대비 미발송 임계점을 확인하고 Slack 알림. 발송된 임계점 리스트 반환."""
    if limit <= 0:
        return []
    ratio = today_cost / limit
    today = date.today().isoformat()
    fired = []

    for threshold in THRESHOLDS:
        if ratio < threshold:
            continue
        already = execute_query(
            "SELECT id FROM daily_cost_alerts WHERE alert_date = %s AND threshold = %s",
            (today, threshold), fetch=True,
        )
        if already:
            continue

        try:
            execute_query(
                "INSERT INTO daily_cost_alerts (alert_date, threshold, today_cost) VALUES (%s, %s, %s)",
                (today, threshold, round(today_cost, 4)),
            )
        except Exception:
            continue

        _send_alert(threshold, today_cost, limit, logger)
        fired.append(threshold)

    return fired


def _send_alert(threshold: float, today_cost: float, limit: float, logger: HarnessLogger | None = None):
    pct = int(threshold * 100)
    remaining = max(0.0, limit - today_cost)
    emoji = ":warning:" if threshold < 1.0 else ":octagonal_sign:"
    title = f"{emoji} Claude API 비용 {pct}% 도달 — ${today_cost:.4f} / ${limit:.2f}"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": title}},
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*오늘 누적*\n${today_cost:.4f}"},
                {"type": "mrkdwn", "text": f"*일일 한도*\n${limit:.2f}"},
                {"type": "mrkdwn", "text": f"*잔여 예산*\n${remaining:.4f}"},
                {"type": "mrkdwn", "text": f"*임계점*\n{pct}%"},
            ],
        },
    ]
    if threshold >= 1.0:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":octagonal_sign: *한도 초과 — Tier 3 신규 호출 차단됨.*\n내일 리셋 전까지 Claude API 호출이 중단됩니다."},
        })
    elif threshold >= 0.9:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":warning: *잔여 10% 이하 — QA LLM 검사 자동 스킵 중.*\nTier 3 배치 크기 축소 권장."},
        })

    try:
        send_slack_route("exec_daily_brief", {"text": title, "blocks": blocks})
        if logger:
            logger.info(f"비용 알림 발송: {pct}% (${today_cost:.4f})")
    except Exception as exc:
        if logger:
            logger.warning(f"비용 알림 Slack 전송 실패: {exc}")
