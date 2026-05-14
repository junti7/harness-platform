"""
T-06: Free→Paid 전환 추적 헬퍼

subscriber_snapshots의 전일 대비 paid_subscribers 증가분을 감지해
subscriber_conversion_events에 기록한다.
"""
from datetime import date, timedelta
from typing import Optional

from core.database import execute_query
from core.logger import HarnessLogger


def get_previous_paid_count(platform: str, before_date: str) -> Optional[int]:
    """before_date 이전 가장 최근 스냅샷의 paid_subscribers 수 반환."""
    result = execute_query(
        """SELECT paid_subscribers FROM subscriber_snapshots
           WHERE platform = %s AND snapshot_date < %s
           ORDER BY snapshot_date DESC LIMIT 1""",
        (platform, before_date), fetch=True,
    )
    if result and result[0]["paid_subscribers"] is not None:
        return int(result[0]["paid_subscribers"])
    return None


def record_conversion_events(
    new_paid: int,
    prev_paid: int,
    snapshot_date: str,
    platform: str = "substack",
    plan: str = "paid_9900_krw",
    logger: Optional[HarnessLogger] = None,
) -> int:
    """delta만큼 subscriber_conversion_events INSERT. 삽입 건수 반환."""
    delta = new_paid - prev_paid
    if delta <= 0:
        return 0

    inserted = 0
    for _ in range(delta):
        execute_query(
            """INSERT INTO subscriber_conversion_events
                   (event_type, plan, source, snapshot_date, notes)
               VALUES ('free_to_paid', %s, %s, %s, %s)""",
            (plan, platform, snapshot_date, f"delta +{delta} from {prev_paid}→{new_paid}"),
        )
        inserted += 1

    if logger:
        logger.info(f"전환 이벤트 기록: +{delta}명 ({prev_paid}→{new_paid}) [{snapshot_date}]")
    return inserted


def detect_and_record_upgrades(
    snapshot_date: str,
    new_paid: int,
    platform: str = "substack",
    logger: Optional[HarnessLogger] = None,
) -> int:
    """전일 대비 delta 감지 후 이벤트 기록. 삽입 건수 반환."""
    prev = get_previous_paid_count(platform, snapshot_date)
    if prev is None:
        if logger:
            logger.info("이전 스냅샷 없음 — 전환 이벤트 생성 생략")
        return 0
    return record_conversion_events(new_paid, prev, snapshot_date, platform, logger=logger)
