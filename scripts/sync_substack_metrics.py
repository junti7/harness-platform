"""
T-04: Substack 구독자/게시물 지표 → subscriber_snapshots 동기화

사용법:
  python scripts/sync_substack_metrics.py              # 오늘 날짜
  python scripts/sync_substack_metrics.py --date 2026-05-14
  python scripts/sync_substack_metrics.py --free 5 --paid 0  # 수동 입력

자동화:
  Mac Mini LaunchAgent: 매일 23:00 KST
  (infra/setup_mac_mini.sh에 cron 등록 포함)
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from core.database import execute_query
from core.logger import HarnessLogger
from core.conversion import detect_and_record_upgrades
from adapters.content.substack_publisher import fetch_subscriber_metrics


def upsert_snapshot(
    snapshot_date: str,
    platform: str,
    free_subscribers: int | None,
    paid_subscribers: int | None,
    post_count: int | None,
    draft_count: int | None,
    notes: str,
) -> int:
    existing = execute_query(
        "SELECT id FROM subscriber_snapshots WHERE snapshot_date = %s AND platform = %s",
        (snapshot_date, platform), fetch=True,
    )
    if existing:
        execute_query("""
            UPDATE subscriber_snapshots
            SET free_subscribers = COALESCE(%s, free_subscribers),
                paid_subscribers = COALESCE(%s, paid_subscribers),
                opens = COALESCE(%s, opens),
                notes = %s
            WHERE id = %s
        """, (
            free_subscribers,
            paid_subscribers,
            post_count,
            notes,
            existing[0]["id"],
        ))
        return existing[0]["id"]

    result = execute_query("""
        INSERT INTO subscriber_snapshots
            (snapshot_date, platform, free_subscribers, paid_subscribers, opens, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        snapshot_date,
        platform,
        free_subscribers or 0,
        paid_subscribers or 0,
        post_count or 0,
        notes,
    ), fetch=True)
    return result[0]["id"] if result else None


def main():
    parser = argparse.ArgumentParser(description="Substack 지표 → subscriber_snapshots 동기화")
    parser.add_argument("--date", default=str(date.today()), help="스냅샷 날짜 (YYYY-MM-DD)")
    parser.add_argument("--free", type=int, default=None, help="무료 구독자 수 수동 입력")
    parser.add_argument("--paid", type=int, default=None, help="유료 구독자 수 수동 입력")
    args = parser.parse_args()

    logger = HarnessLogger(tier=4, correlation_id="metrics-sync")
    logger.info(f"=== Substack 지표 동기화 시작 ({args.date}) ===")

    if args.free is not None or args.paid is not None:
        metrics = {
            "free_subscribers": args.free,
            "paid_subscribers": args.paid,
            "post_count": None,
            "draft_count": None,
            "notes": "수동 입력",
        }
        logger.info(f"수동 입력: free={args.free}, paid={args.paid}")
    else:
        metrics = fetch_subscriber_metrics(logger)
        logger.info(
            f"수집 완료: free={metrics['free_subscribers']}, paid={metrics['paid_subscribers']}, "
            f"posts={metrics['post_count']}, drafts={metrics['draft_count']}"
        )

    if not os.getenv("SUBSTACK_SESSION_TOKEN") and args.free is None:
        logger.error("SUBSTACK_SESSION_TOKEN 미설정. --free/--paid로 수동 입력하거나 .env 확인")
        sys.exit(1)

    snapshot_id = upsert_snapshot(
        snapshot_date=args.date,
        platform="substack",
        free_subscribers=metrics["free_subscribers"],
        paid_subscribers=metrics["paid_subscribers"],
        post_count=metrics["post_count"],
        draft_count=metrics["draft_count"],
        notes=metrics.get("notes", ""),
    )

    logger.info(f"subscriber_snapshots 저장: id={snapshot_id}")

    if metrics.get("paid_subscribers") is not None:
        upgrades = detect_and_record_upgrades(
            snapshot_date=args.date,
            new_paid=metrics["paid_subscribers"],
            platform="substack",
            logger=logger,
        )
        if upgrades:
            print(f"   🎉 전환 이벤트: +{upgrades}명 유료 전환 감지")

    print(f"\n✅ 완료 ({args.date})")
    print(f"   free={metrics['free_subscribers']}  paid={metrics['paid_subscribers']}")
    print(f"   posts={metrics['post_count']}  drafts={metrics['draft_count']}")
    if metrics.get("notes"):
        print(f"   note: {metrics['notes']}")


if __name__ == "__main__":
    main()
