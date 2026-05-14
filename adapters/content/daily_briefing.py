import os
from datetime import date, timedelta

from dotenv import load_dotenv

from adapters.content.mobile_dispatcher import send_decision_card
from adapters.content.slack_router import send_slack_route
from core.database import execute_query
from core.logger import HarnessLogger


load_dotenv()

DEFAULT_LIMIT = int(os.getenv("MOBILE_BRIEFING_LIMIT", "5"))
DEFAULT_CHANNEL = os.getenv("MOBILE_BRIEFING_CHANNEL", "text")


def get_briefing_candidates(limit: int = DEFAULT_LIMIT) -> list[dict]:
    return execute_query("""
        SELECT
            s.id,
            s.signal_summary,
            s.signal_type,
            s.preliminary_score,
            s.monetization_potential,
            s.source_confidence,
            s.created_at
        FROM signals s
        LEFT JOIN partner_feedback pf
            ON pf.target_type = 'signal' AND pf.target_id = s.id
        LEFT JOIN ceo_decisions cd
            ON cd.target_type = 'signal' AND cd.target_id = s.id
        WHERE s.status = 'candidate'
          AND pf.id IS NULL
          AND cd.id IS NULL
        ORDER BY
            s.preliminary_score DESC,
            s.monetization_potential DESC,
            s.source_confidence DESC,
            s.created_at DESC
        LIMIT %s
    """, (limit,), fetch=True)


def send_daily_mobile_briefing(
    limit: int = DEFAULT_LIMIT,
    channel: str = DEFAULT_CHANNEL,
    correlation_id: str = None,
) -> dict:
    logger = HarnessLogger(tier=4, correlation_id=correlation_id)
    logger.info(f"=== Daily mobile briefing 시작 (limit={limit}, channel={channel}) ===")

    candidates = get_briefing_candidates(limit)
    if not candidates:
        logger.info("모바일 브리핑 후보 없음")
        return {"sent": 0, "candidates": 0, "items": []}

    results = []
    for row in candidates:
        signal_id = row["id"]
        try:
            result = send_decision_card("signal", signal_id, channel=channel)
            results.append({
                "signal_id": signal_id,
                "channel": channel,
                "sent": result.get("sent", False),
                "text": result.get("text"),
            })
            logger.info(f"Decision card 처리 완료: signal#{signal_id}")
        except Exception as e:
            logger.error(f"Decision card 처리 실패: signal#{signal_id} ({type(e).__name__}: {e})")
            results.append({
                "signal_id": signal_id,
                "channel": channel,
                "sent": False,
                "error": f"{type(e).__name__}: {e}",
            })

    sent = sum(1 for item in results if item.get("sent") or channel in {"text", "json"})
    logger.info(f"=== Daily mobile briefing 완료: {sent}/{len(candidates)} ===")
    return {"sent": sent, "candidates": len(candidates), "items": results}


def get_daily_kpis(today: str | None = None) -> dict:
    """어제 기준 KPI 집계 — T-16 대시보드용."""
    today = today or str(date.today())
    yesterday = str(date.fromisoformat(today) - timedelta(days=1))

    def _q(sql, *args):
        return execute_query(sql, args if args else None, fetch=True)

    # 구독자
    snap = _q(
        "SELECT free_subscribers, paid_subscribers FROM subscriber_snapshots WHERE snapshot_date = %s AND platform = 'substack'",
        yesterday,
    )
    snap_prev = _q(
        "SELECT free_subscribers, paid_subscribers FROM subscriber_snapshots WHERE snapshot_date < %s AND platform = 'substack' ORDER BY snapshot_date DESC LIMIT 1",
        yesterday,
    )
    free_now = int((snap[0].get("free_subscribers") or 0) if snap else 0)
    paid_now = int((snap[0].get("paid_subscribers") or 0) if snap else 0)
    free_prev = int((snap_prev[0].get("free_subscribers") or 0) if snap_prev else 0)
    paid_prev = int((snap_prev[0].get("paid_subscribers") or 0) if snap_prev else 0)

    # 전환
    conv = _q(
        "SELECT COUNT(*) as cnt FROM subscriber_conversion_events WHERE snapshot_date = %s",
        yesterday,
    )

    # 파이프라인
    runs = _q(
        "SELECT status, COUNT(*) as cnt FROM pipeline_runs WHERE DATE(created_at) = %s GROUP BY status",
        yesterday,
    )
    run_map = {r.get("status"): r.get("cnt") for r in runs}

    # 비용
    cost = _q(
        """SELECT COALESCE(SUM(
            (input_tokens::float/1000*0.003) + (output_tokens::float/1000*0.015)
           ), 0) as c
           FROM api_cost_log WHERE provider='anthropic' AND DATE(created_at) = %s""",
        yesterday,
    )
    daily_cost = float(cost[0].get("c", 0) if cost else 0)

    # 상위 독자 피드백 인텐트
    top_feedback = _q(
        """SELECT event_key, COUNT(*) as cnt FROM customer_memory_events
           WHERE event_type='reader_feedback' AND DATE(created_at) = %s
           GROUP BY event_key ORDER BY cnt DESC LIMIT 1""",
        yesterday,
    )

    return {
        "date": yesterday,
        "free_subscribers": free_now,
        "free_delta": free_now - free_prev,
        "paid_subscribers": paid_now,
        "paid_delta": paid_now - paid_prev,
        "conversions": int(conv[0].get("cnt", 0) if conv else 0),
        "pipeline_ok": int(run_map.get("success", run_map.get("ok", 0))),
        "pipeline_fail": int(run_map.get("failed", run_map.get("error", 0))),
        "daily_cost_usd": round(daily_cost, 4),
        "top_feedback": top_feedback[0].get("event_key", "") if top_feedback else "",
    }


def send_kpi_slack_card(kpis: dict, logger: HarnessLogger | None = None) -> None:
    """T-16: KPI Slack 카드를 exec_daily_brief 채널에 발송."""
    d = kpis["date"]
    free_arrow = "↑" if kpis["free_delta"] > 0 else ("↓" if kpis["free_delta"] < 0 else "—")
    paid_arrow = "↑" if kpis["paid_delta"] > 0 else ("↓" if kpis["paid_delta"] < 0 else "—")
    run_status = "✅" if kpis["pipeline_fail"] == 0 else f"⚠️ 실패 {kpis['pipeline_fail']}건"

    lines = [
        f"*📊 Daily KPI — {d}*",
        f"구독자  무료 {kpis['free_subscribers']} {free_arrow}{abs(kpis['free_delta'])}  유료 {kpis['paid_subscribers']} {paid_arrow}{abs(kpis['paid_delta'])}",
        f"전환 {kpis['conversions']}건  |  파이프라인 {run_status}",
        f"Claude 비용 ${kpis['daily_cost_usd']:.4f}",
    ]
    if kpis.get("top_feedback"):
        lines.append(f"독자 피드백 최다: {kpis['top_feedback']}")

    text = "\n".join(lines)
    try:
        send_slack_route("exec_daily_brief", {"text": text})
        if logger:
            logger.info("KPI Slack 카드 발송 완료")
    except Exception as e:
        if logger:
            logger.warning(f"KPI Slack 발송 실패: {e}")


if __name__ == "__main__":
    send_daily_mobile_briefing()
