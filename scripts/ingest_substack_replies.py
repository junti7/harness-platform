"""
T-05: Substack 댓글/답글 → customer_memory_events 수집

사용법:
  python scripts/ingest_substack_replies.py              # 최근 발행 이슈 자동 탐색
  python scripts/ingest_substack_replies.py --post-id 12345
  python scripts/ingest_substack_replies.py --dry-run    # DB 저장 없이 출력만

자동화:
  Mac Mini LaunchAgent: 매일 08:00 KST (Substack 댓글 배치 수집)
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

import httpx

from core.database import execute_query
from core.logger import HarnessLogger
from core.reader_feedback import classify_feedback, hash_email, record_feedback, upsert_reader_profile

SUBSTACK_SESSION = os.getenv("SUBSTACK_SESSION_TOKEN", "")
SUBSTACK_PUBLICATION = os.getenv("SUBSTACK_PUBLICATION_URL", "https://harness.substack.com")

_SESSION_HEADERS = {
    "Cookie": f"substack.sid={SUBSTACK_SESSION}" if SUBSTACK_SESSION else "",
    "User-Agent": "Mozilla/5.0 (compatible; HarnessPipeline/1.0)",
}


def _fetch_comments(post_id: int, logger: HarnessLogger) -> list[dict]:
    """Substack 포스트의 최상위 댓글 목록 반환."""
    url = f"{SUBSTACK_PUBLICATION}/api/v1/post/{post_id}/comments"
    try:
        resp = httpx.get(url, headers=_SESSION_HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("comments", data if isinstance(data, list) else [])
        logger.warning(f"댓글 API {resp.status_code}: post_id={post_id}")
    except Exception as e:
        logger.warning(f"댓글 조회 실패 (post_id={post_id}): {e}")
    return []


def _fetch_recent_post_ids(logger: HarnessLogger) -> list[int]:
    """DB에서 최근 newsletter_issues의 Substack post_id 목록 조회."""
    rows = execute_query(
        """SELECT external_id FROM newsletter_issues
           WHERE external_id IS NOT NULL
           ORDER BY published_at DESC NULLS LAST
           LIMIT 10""",
        fetch=True,
    )
    ids = []
    for r in rows:
        try:
            ids.append(int(r["external_id"]))
        except (TypeError, ValueError):
            pass
    if not ids:
        logger.info("DB에 Substack post_id 없음 — --post-id로 직접 지정 필요")
    return ids


def process_comment(comment: dict, post_id: int, dry_run: bool, logger: HarnessLogger) -> bool:
    """단일 댓글을 분류·저장. 저장 성공 시 True 반환."""
    author = comment.get("name") or comment.get("author_name") or "anonymous"
    author_id = comment.get("author_id") or comment.get("user_id") or ""
    email = comment.get("email", "")
    body = (comment.get("body") or comment.get("content") or "").strip()

    if not body:
        return False

    classification = classify_feedback(body)
    external_ref = f"substack:{author_id}" if author_id else f"substack_anon:{hash_email(author)}"
    email_hash = hash_email(email) if email else None

    logger.info(f"  댓글: {author!r} [{classification['intent']}] {body[:60]!r}")

    if dry_run:
        return True

    customer_id = upsert_reader_profile(external_ref, email_hash)
    record_feedback(customer_id, body, classification, f"substack_comment:{post_id}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Substack 댓글 → customer_memory_events 수집")
    parser.add_argument("--post-id", type=int, default=None, help="특정 Substack post_id")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 출력만")
    args = parser.parse_args()

    logger = HarnessLogger(tier=4, correlation_id="substack-replies")
    logger.info(f"=== Substack 댓글 수집 시작 ({date.today()}) ===")

    if not SUBSTACK_SESSION:
        logger.error("SUBSTACK_SESSION_TOKEN 미설정. .env 확인")
        sys.exit(1)

    post_ids = [args.post_id] if args.post_id else _fetch_recent_post_ids(logger)
    if not post_ids:
        print("처리할 포스트 없음")
        sys.exit(0)

    total_saved = 0
    for post_id in post_ids:
        comments = _fetch_comments(post_id, logger)
        logger.info(f"post_id={post_id}: 댓글 {len(comments)}개")
        for comment in comments:
            if process_comment(comment, post_id, args.dry_run, logger):
                total_saved += 1

    tag = "[dry-run] " if args.dry_run else ""
    print(f"\n✅ {tag}완료: {total_saved}개 댓글 처리")


if __name__ == "__main__":
    main()
