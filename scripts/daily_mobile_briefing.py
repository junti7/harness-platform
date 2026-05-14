import argparse
import json
import sys

sys.path.insert(0, ".")

from adapters.content.daily_briefing import send_daily_mobile_briefing, get_daily_kpis, send_kpi_slack_card
from core.logger import HarnessLogger


def main():
    parser = argparse.ArgumentParser(description="Send or preview the daily mobile decision briefing.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--channel", choices=["text", "json", "slack"], default="text")
    parser.add_argument("--kpi-only", action="store_true", help="KPI 카드만 Slack 발송")
    args = parser.parse_args()

    if args.kpi_only:
        logger = HarnessLogger(tier=4, correlation_id="kpi-card")
        kpis = get_daily_kpis()
        send_kpi_slack_card(kpis, logger)
        print(f"KPI 카드 발송 완료: {kpis['date']}")
        return

    result = send_daily_mobile_briefing(limit=args.limit, channel=args.channel)

    # T-16: signal briefing과 함께 KPI 카드도 발송 (--channel slack 시)
    if args.channel == "slack":
        logger = HarnessLogger(tier=4, correlation_id="kpi-card")
        send_kpi_slack_card(get_daily_kpis(), logger)
    if args.channel == "text":
        for item in result["items"]:
            if item.get("text"):
                print(item["text"])
                print("\n" + "=" * 72 + "\n")
            elif item.get("error"):
                print(f"signal#{item['signal_id']} error: {item['error']}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
