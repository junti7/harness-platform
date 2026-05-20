"""
T-08: Claude API 일일 비용 임계점 Slack 알림 + CEO 승인 한도 확장

임계점: 50% / 90% / 100% of effective daily limit
- 이미 발송된 임계점은 당일 재발송 안 함 (idempotent)
- 50%/100%: SLACK_CHANNEL_EXEC_DAILY_BRIEF 채널
- 90%: exec_president_decisions 채널 + CEO 한도 확장 승인 요청
- CEO 승인 시 한도 +$1, 월말까지 유효, 다음 달 자동 복원
"""
import os
from calendar import monthrange
from datetime import date

from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.slack_router import send_slack_route

THRESHOLDS = [0.50, 0.90, 1.00]

_SOURCE_LABEL = {"pipeline": "파이프라인", "openclaw": "OpenClaw"}


def get_effective_limit(source: str, base_limit: float) -> float:
    """CEO 승인 override가 유효하면 반환, 없으면 base_limit 반환."""
    try:
        result = execute_query(
            "SELECT override_limit FROM cost_limit_overrides WHERE source = %s AND valid_until >= CURRENT_DATE ORDER BY created_at DESC LIMIT 1",
            (source,), fetch=True,
        )
        if result:
            return float(result[0]["override_limit"])
    except Exception:
        pass
    return base_limit


def apply_ceo_override(source: str, base_limit: float) -> float:
    """한도를 +$1 올려 이번 달 말까지 적용하고, override_limit을 반환."""
    override_limit = base_limit + 1.0
    today = date.today()
    last_day = date(today.year, today.month, monthrange(today.year, today.month)[1])
    execute_query(
        "INSERT INTO cost_limit_overrides (source, base_limit, override_limit, valid_until) VALUES (%s, %s, %s, %s)",
        (source, base_limit, override_limit, last_day),
    )
    return override_limit


def check_and_alert(today_cost: float, limit: float, logger: HarnessLogger | None = None, source: str = "pipeline") -> list[float]:
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
            "SELECT id FROM daily_cost_alerts WHERE alert_date = %s AND threshold = %s AND source = %s",
            (today, threshold, source), fetch=True,
        )
        if already:
            continue

        try:
            execute_query(
                "INSERT INTO daily_cost_alerts (alert_date, threshold, today_cost, source) VALUES (%s, %s, %s, %s)",
                (today, threshold, round(today_cost, 4), source),
            )
        except Exception:
            continue

        _send_alert(threshold, today_cost, limit, source, logger)
        fired.append(threshold)

    return fired


def _send_alert(threshold: float, today_cost: float, limit: float, source: str = "pipeline", logger: HarnessLogger | None = None):
    pct = int(threshold * 100)
    remaining = max(0.0, limit - today_cost)
    emoji = ":warning:" if threshold < 1.0 else ":octagonal_sign:"
    label = _SOURCE_LABEL.get(source, source)
    title = f"{emoji} [{label}] Claude API 비용 {pct}% 도달 — ${today_cost:.4f} / ${limit:.2f}"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": title}},
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*구분*\n{label}"},
                {"type": "mrkdwn", "text": f"*오늘 누적*\n${today_cost:.4f}"},
                {"type": "mrkdwn", "text": f"*일일 한도*\n${limit:.2f}"},
                {"type": "mrkdwn", "text": f"*잔여 예산*\n${remaining:.4f}"},
            ],
        },
    ]

    if threshold >= 1.0:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": ":octagonal_sign: *한도 초과 — 유료 LLM 호출 차단됨.*\n내일 자정 리셋 전까지 Claude API 호출이 중단됩니다."},
        })
        route = "exec_daily_brief"
    elif threshold >= 0.9:
        approve_keyword = f"{label} 한도 확장 승인"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":warning: *잔여 10% 이하 — 한도 소진 임박.*\n"
                    f"한도를 +$1 올려 이번 달 말까지 연장하려면 OpenClaw에게 아래 메시지를 보내주세요:\n"
                    f"```{approve_keyword}```\n"
                    f"승인 시: ${limit:.2f} → ${limit + 1:.2f} ({date.today().strftime('%m')}월 말까지, 다음 달 자동 복원)"
                ),
            },
        })
        route = "exec_president_decisions"
    else:
        route = "exec_daily_brief"

    try:
        send_slack_route(route, {"text": title, "blocks": blocks})
        if logger:
            logger.info(f"비용 알림 발송: [{source}] {pct}% (${today_cost:.4f})")
    except Exception as exc:
        if logger:
            logger.warning(f"비용 알림 Slack 전송 실패: {exc}")
