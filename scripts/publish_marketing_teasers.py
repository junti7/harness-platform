"""
T-07: 마케팅 티저 생성 및 게시 CLI

사용법:
  python scripts/publish_marketing_teasers.py --issue-id 1 --dry-run
  python scripts/publish_marketing_teasers.py --issue-id 1 --publish --platform x
  python scripts/publish_marketing_teasers.py --issue-id 1 --publish  # 전 플랫폼

필요 승인 (--publish 시):
  qa_clear + legal_review_approve (CLAUDE.md §4, §5)

환경 변수 (.env):
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
  LINKEDIN_ACCESS_TOKEN, LINKEDIN_PERSON_URN
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from core.database import execute_query
from core.logger import HarnessLogger
from adapters.marketing.teaser_generator import generate_teasers


def _save_draft(issue_id: int, platform: str, content: str) -> int:
    result = execute_query(
        """INSERT INTO marketing_posts
               (newsletter_issue_id, platform, content, status)
           VALUES (%s, %s, %s, 'draft')
           RETURNING id""",
        (issue_id, platform, content), fetch=True,
    )
    return result[0]["id"] if result else None


def _mark_posted(post_id: int, public_url: str) -> None:
    execute_query(
        "UPDATE marketing_posts SET status='posted', public_url=%s WHERE id=%s",
        (public_url, post_id),
    )


def _mark_failed(post_id: int, error: str) -> None:
    execute_query(
        "UPDATE marketing_posts SET status='failed', error_message=%s WHERE id=%s",
        (str(error)[:500], post_id),
    )


def _publish_platform(platform: str, content: str, issue_id: int, logger: HarnessLogger) -> bool:
    post_id = _save_draft(issue_id, platform, content)
    try:
        if platform == "x":
            from adapters.marketing.x_publisher import post_tweet
            result = post_tweet(content)
        elif platform == "linkedin":
            from adapters.marketing.linkedin_publisher import post_to_linkedin
            result = post_to_linkedin(content)
        else:
            logger.warning(f"알 수 없는 플랫폼: {platform}")
            return False

        if post_id:
            _mark_posted(post_id, result.get("url", ""))
        logger.info(f"[{platform}] 게시 완료: {result.get('url', '')}")
        return True
    except Exception as e:
        if post_id:
            _mark_failed(post_id, str(e))
        logger.error(f"[{platform}] 게시 실패: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="마케팅 티저 생성 및 게시")
    parser.add_argument("--issue-id", type=int, required=True, help="newsletter_issues.id")
    parser.add_argument("--dry-run", action="store_true", help="생성만, DB/외부 게시 없음")
    parser.add_argument("--publish", action="store_true", help="실제 게시 (API 키 필요)")
    parser.add_argument("--platform", choices=["x", "linkedin", "substack_note", "all"], default="all")
    args = parser.parse_args()

    if args.publish and not args.dry_run:
        print("⚠️  --publish 모드: qa_clear + legal_review_approve 완료 확인 후 사용하세요.")

    logger = HarnessLogger(tier=4, correlation_id=f"marketing-{args.issue_id}")
    logger.info(f"=== 마케팅 티저 생성 시작 (issue_id={args.issue_id}) ===")

    teasers = generate_teasers(args.issue_id, logger)

    platform_map = {
        "x": teasers.get("x_post", ""),
        "linkedin": teasers.get("linkedin_post", ""),
        "substack_note": teasers.get("substack_note", ""),
    }

    print("\n" + "=" * 60)
    for platform, content in platform_map.items():
        if args.platform != "all" and args.platform != platform:
            continue
        print(f"\n[{platform.upper()}]")
        print(content)
        print(f"  ({len(content)}자)")

    if args.dry_run:
        print("\n✅ dry-run 완료 (DB/외부 게시 없음)")
        return

    if args.publish:
        for platform, content in platform_map.items():
            if args.platform != "all" and args.platform != platform:
                continue
            if platform == "substack_note":
                post_id = _save_draft(args.issue_id, platform, content)
                logger.info(f"[substack_note] 드래프트 저장 id={post_id} (Substack API 미지원)")
                continue
            _publish_platform(platform, content, args.issue_id, logger)
    else:
        for platform, content in platform_map.items():
            if args.platform != "all" and args.platform != platform:
                continue
            post_id = _save_draft(args.issue_id, platform, content)
            logger.info(f"[{platform}] draft 저장: id={post_id}")
        print("\n✅ draft 저장 완료 (--publish 없음, marketing_posts.status='draft')")


if __name__ == "__main__":
    main()
