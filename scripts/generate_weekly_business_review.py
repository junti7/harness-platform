"""
T-15: 주간 사업 현황 리포트 자동 생성

사용법:
  python scripts/generate_weekly_business_review.py
  python scripts/generate_weekly_business_review.py --week-start 2026-05-11

자동화:
  Mac Mini LaunchAgent: 매주 금요일 18:00 KST

결과:
  docs/reports/WBR-YYYY-MM-DD.md
  SLACK_CHANNEL_EXEC_DAILY_BRIEF 채널 요약 카드
"""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.slack_router import send_slack_route

_OUTPUT_DIR = Path("docs/reports")


def _get_kpis(week_start: date, week_end: date) -> dict:
    """7일 KPI 집계."""
    prev_start = week_start - timedelta(days=7)

    def _q(sql, *args):
        return execute_query(sql, args if args else None, fetch=True)

    # 구독자
    sub_curr = _q(
        "SELECT free_subscribers, paid_subscribers FROM subscriber_snapshots WHERE snapshot_date <= %s ORDER BY snapshot_date DESC LIMIT 1",
        str(week_end),
    )
    sub_prev = _q(
        "SELECT free_subscribers, paid_subscribers FROM subscriber_snapshots WHERE snapshot_date <= %s ORDER BY snapshot_date DESC LIMIT 1",
        str(prev_start),
    )
    free_now = int((sub_curr[0].get("free_subscribers") or 0) if sub_curr else 0)
    paid_now = int((sub_curr[0].get("paid_subscribers") or 0) if sub_curr else 0)
    free_prev = int((sub_prev[0].get("free_subscribers") or 0) if sub_prev else 0)
    paid_prev = int((sub_prev[0].get("paid_subscribers") or 0) if sub_prev else 0)

    # 전환 이벤트
    conv = _q(
        "SELECT COUNT(*) as cnt FROM subscriber_conversion_events WHERE event_type='free_to_paid' AND snapshot_date BETWEEN %s AND %s",
        str(week_start), str(week_end),
    )
    conversions = int(conv[0].get("cnt", 0) if conv else 0)

    # 이슈 발행
    issues = _q(
        "SELECT id, title, status FROM newsletter_issues WHERE issue_date BETWEEN %s AND %s ORDER BY id",
        str(week_start), str(week_end),
    )

    # 파이프라인 비용
    cost = _q(
        """SELECT provider, COALESCE(SUM(
            CASE
                WHEN provider = 'anthropic' THEN (input_tokens::float/1000*0.003) + (output_tokens::float/1000*0.015)
                WHEN provider = 'google' THEN (input_tokens::float/1000*0.0035) + (output_tokens::float/1000*0.0105)
                ELSE 0
            END
           ), 0) as total_cost
           FROM api_cost_log
           WHERE DATE(created_at) BETWEEN %s AND %s
           GROUP BY provider""",
        str(week_start), str(week_end),
    )
    total_cost = sum(float(c.get("total_cost", 0)) for c in cost)
    cost_by_provider = {c.get("provider"): round(float(c.get("total_cost", 0)), 4) for c in cost}


    # 상위 시그널
    signals = _q(
        """SELECT ro.final_title FROM refined_outputs ro
           WHERE DATE(ro.created_at) BETWEEN %s AND %s
           ORDER BY ro.id DESC LIMIT 3""",
        str(week_start), str(week_end),
    )

    # 독자 피드백
    feedback = _q(
        """SELECT event_key, COUNT(*) as cnt FROM customer_memory_events
           WHERE event_type='reader_feedback' AND DATE(created_at) BETWEEN %s AND %s
           GROUP BY event_key ORDER BY cnt DESC LIMIT 3""",
        str(week_start), str(week_end),
    )

    return {
        "week_start": str(week_start),
        "week_end": str(week_end),
        "free_subscribers": free_now,
        "paid_subscribers": paid_now,
        "free_delta": free_now - free_prev,
        "paid_delta": paid_now - paid_prev,
        "conversions": conversions,
        "issues_published": [dict(r) for r in issues],
        "total_cost_usd": round(total_cost, 4),
        "cost_by_provider": cost_by_provider,
        "top_signals": [r.get("final_title", "") for r in signals],
        "feedback_themes": [{"intent": r.get("event_key"), "count": r.get("cnt")} for r in feedback],
    }


def _write_report(kpis: dict) -> Path:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = _OUTPUT_DIR / f"WBR-{kpis['week_end']}.md"

    issues_md = "\n".join(
        f"  - #{r['id']} {r.get('title', '')} [{r.get('status', '')}]"
        for r in kpis["issues_published"]
    ) or "  - (없음)"

    signals_md = "\n".join(f"  - {t}" for t in kpis["top_signals"]) or "  - (없음)"
    feedback_md = "\n".join(
        f"  - {r['intent']}: {r['count']}건" for r in kpis["feedback_themes"]
    ) or "  - (없음)"
    
    cost_breakdown = ", ".join(f"{p.capitalize()}: ${c:.4f}" for p, c in kpis["cost_by_provider"].items())

    path.write_text(
        f"# Weekly Business Review — {kpis['week_start']} ~ {kpis['week_end']}\n\n"
        f"## 구독자\n"
        f"- 무료: {kpis['free_subscribers']}명 ({kpis['free_delta']:+d})\n"
        f"- 유료: {kpis['paid_subscribers']}명 ({kpis['paid_delta']:+d})\n"
        f"- 전환 이벤트: {kpis['conversions']}건\n\n"
        f"## 콘텐츠\n{issues_md}\n\n"
        f"## 비용\n"
        f"- Total LLM API: ${kpis['total_cost_usd']:.4f} ({cost_breakdown})\n\n"
        f"## 주요 분석\n{signals_md}\n\n"
        f"## 독자 피드백 테마\n{feedback_md}\n\n"
        f"---\n> Generated by Harness Weekly Business Review Agent\n",
        encoding="utf-8",
    )
    return path


def _post_slack_summary(kpis: dict, report_path: Path) -> None:
    text = (
        f"📊 *주간 사업 현황* ({kpis['week_start']}~{kpis['week_end']})\n"
        f"구독자: 무료 {kpis['free_subscribers']} ({kpis['free_delta']:+d}) | "
        f"유료 {kpis['paid_subscribers']} ({kpis['paid_delta']:+d})\n"
        f"전환: {kpis['conversions']}건 | 총비용: ${kpis['total_cost_usd']:.4f}\n"
        f"이슈 {len(kpis['issues_published'])}개 발행\n"
        f"전체 리포트: {report_path}"
    )
    send_slack_route("exec_daily_brief", {"text": text})


def main():
    parser = argparse.ArgumentParser(description="주간 사업 현황 리포트 생성")
    parser.add_argument("--week-start", default=str(date.today() - timedelta(days=6)))
    parser.add_argument("--no-slack", action="store_true")
    args = parser.parse_args()

    week_start = date.fromisoformat(args.week_start)
    week_end = week_start + timedelta(days=6)

    logger = HarnessLogger(tier=4, correlation_id="wbr")
    logger.info(f"=== 주간 사업 현황 리포트 ({week_start}~{week_end}) ===")

    kpis = _get_kpis(week_start, week_end)
    report_path = _write_report(kpis)
    logger.info(f"리포트 저장: {report_path}")

    if not args.no_slack:
        try:
            _post_slack_summary(kpis, report_path)
            logger.info("Slack 요약 발송 완료")
        except Exception as e:
            logger.warning(f"Slack 발송 실패: {e}")

    print(f"\n✅ 완료: {report_path}")
    print(f"   구독자 무료 {kpis['free_subscribers']} ({kpis['free_delta']:+d})")
    print(f"   유료 {kpis['paid_subscribers']} ({kpis['paid_delta']:+d})")
    print(f"   Claude 비용 ${kpis['total_cost_usd']:.4f}")


if __name__ == "__main__":
    main()
