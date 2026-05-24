"""
T-09: 법률 사전 검토 CLI

사용법:
  python scripts/run_legal_review.py --issue-id 1
  python scripts/run_legal_review.py --text "Tesla 주식 사세요"  # 단일 텍스트 테스트
  python scripts/run_legal_review.py --issue-id 1 --output-only  # 메모 경로만 출력

결과: docs/reviews/legal/NEWSLETTER_ISSUE-{n}-{date}.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.legal_review import run_legal_review


def _fetch_issue_text(issue_id: int) -> str:
    rows = execute_query(
        "SELECT title, free_body FROM newsletter_issues WHERE id = %s",
        (issue_id,), fetch=True,
    )
    if not rows:
        raise ValueError(f"newsletter_issues id={issue_id} 없음")
    r = rows[0]
    return f"{r.get('title') or ''}\n\n{r.get('free_body') or ''}"


def main():
    parser = argparse.ArgumentParser(description="법률 사전 검토")
    parser.add_argument("--issue-id", type=int, default=None, help="newsletter_issues.id")
    parser.add_argument("--text", default=None, help="직접 텍스트 입력 (테스트용)")
    parser.add_argument("--output-only", action="store_true", help="메모 경로만 출력")
    parser.add_argument("--is-approved", action="store_true", help="CEO 승인 후 실제 실행을 트리거")
    args = parser.parse_args()

    if not args.issue_id and not args.text:
        parser.error("--issue-id 또는 --text 필요")

    logger = HarnessLogger(tier=4, correlation_id="legal-review")

    if args.text:
        content = args.text
        target_type = "test"
        target_id = None
    else:
        content = _fetch_issue_text(args.issue_id)
        target_type = "newsletter_issue"
        target_id = args.issue_id

    result = run_legal_review(
        content,
        target_type,
        target_id,
        logger,
        is_approved=args.is_approved,
    )

    if args.output_only:
        print(result["memo_path"])
        return
    
    if result.get("result") == "pending_approval":
        print("\n⏳ CEO 승인 대기 중... (승인 요청이 Slack으로 발송되었습니다)")
        print(f"   {result.get('summary')}")
        return

    print(f"\n{'=' * 60}")
    print(f"결과: {result['result'].upper()}")
    print(f"메모: {result['memo_path']}")
    print(f"승인: {'✅ legal_review_approve' if result['approved'] else '❌ legal_review_block'}")

    findings = result["primary"].get("findings", [])
    if findings:
        print(f"\n발견 사항 ({len(findings)}개):")
        for f in findings:
            print(f"  [{f.get('severity', '').upper()}] {f.get('law', '')}: {f.get('reason', '')[:80]}")

    disclaimer = result["primary"].get("disclaimer_text", "")
    if disclaimer:
        print(f"\nDisclaimer 초안:\n  {disclaimer[:200]}")


if __name__ == "__main__":
    main()
