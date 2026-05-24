"""Maily 발행본 Polling 동기화.

GET https://api.maily.so/api/{newsletter_id}/notes.json 를 주기적으로 호출해
DB newsletter_issues 테이블과 비교, 신규 발행본을 자동 반영한다.

launchd (com.harness.maily-sync) 가 15분마다 실행.
직접 실행: python scripts/sync_maily_posts.py [--once]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env", override=True)

from core.database import execute_query  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [maily-sync] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "logs" / "maily-sync.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

MAILY_API_KEY = os.getenv("MAILY_API_KEY", "")
MAILY_NEWSLETTER_ID = os.getenv("MAILY_NEWSLETTER_ID", "")
MAILY_API_BASE = "https://api.maily.so"
POLL_INTERVAL = int(os.getenv("MAILY_SYNC_INTERVAL_SEC", "900"))  # 15분


def _fetch_notes() -> list[dict]:
    if not MAILY_API_KEY or not MAILY_NEWSLETTER_ID:
        logger.warning("MAILY_API_KEY 또는 MAILY_NEWSLETTER_ID 미설정 — 스킵")
        return []

    url = f"{MAILY_API_BASE}/api/{MAILY_NEWSLETTER_ID}/notes.json"
    resp = requests.get(url, headers={"Authorization": f"Bearer {MAILY_API_KEY}"}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    # API가 배열 또는 {"notes": [...]} 형태 모두 처리
    return data if isinstance(data, list) else data.get("notes", [])


def _get_existing_urls() -> set[str]:
    rows = execute_query(
        "SELECT public_url FROM newsletter_issues WHERE publishing_platform = 'maily' AND public_url IS NOT NULL AND public_url != ''",
        fetch=True,
    )
    return {r["public_url"] for r in rows}


def _upsert_issue(note: dict) -> bool:
    """신규 발행본을 DB에 반영. 변경 발생 시 True 반환."""
    public_url = note.get("url") or note.get("public_url") or ""
    if not public_url:
        return False

    title = note.get("subject") or note.get("title") or "Maily 발행본"
    published_at_raw = note.get("published_at") or note.get("sent_at")
    try:
        published_at = datetime.fromisoformat(published_at_raw.replace("Z", "+00:00")) if published_at_raw else datetime.now()
    except (ValueError, AttributeError):
        published_at = datetime.now()

    existing = execute_query(
        "SELECT id, status FROM newsletter_issues WHERE public_url = %s",
        (public_url,),
        fetch=True,
    )

    if existing:
        row = existing[0]
        if row["status"] != "published":
            execute_query(
                "UPDATE newsletter_issues SET status = 'published', published_at = %s, updated_at = NOW() WHERE id = %s",
                (published_at, row["id"]),
            )
            logger.info(f"[sync] 상태 업데이트: id={row['id']} → published | {title[:50]}")
            return True
        return False

    # 매핑되지 않은 신규 발행본 — 새 레코드 삽입
    execute_query(
        """INSERT INTO newsletter_issues
           (title, publishing_platform, status, public_url, published_at, created_at, updated_at)
           VALUES (%s, 'maily', 'published', %s, %s, NOW(), NOW())""",
        (title, public_url, published_at),
    )
    logger.info(f"[sync] 신규 발행본 등록: {title[:50]} | {public_url}")
    return True


def sync_once() -> int:
    logger.info("Maily 발행본 동기화 시작")
    try:
        notes = _fetch_notes()
    except Exception as e:
        logger.error(f"API 호출 실패: {e}")
        return 0

    if not notes:
        logger.info("발행본 없음 또는 API 키 미설정")
        return 0

    changed = 0
    for note in notes:
        try:
            if _upsert_issue(note):
                changed += 1
        except Exception as e:
            logger.error(f"레코드 처리 실패: {e} | {note.get('url', '?')}")

    logger.info(f"동기화 완료: {changed}건 변경 / {len(notes)}건 확인")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Maily 발행본 polling 동기화")
    parser.add_argument("--once", action="store_true", help="1회 실행 후 종료 (launchd 모드)")
    args = parser.parse_args()

    if args.once:
        sync_once()
        return

    logger.info(f"polling 루프 시작 (간격: {POLL_INTERVAL}s)")
    while True:
        sync_once()
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
