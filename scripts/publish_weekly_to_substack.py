"""
Weekly Newsletter → Substack 발행 스크립트

사용법:
  # Draft만 생성 (기본, 발행 전 검토용)
  python scripts/publish_weekly_to_substack.py --issue 1 --date 2026-05-11

  # Draft 생성 + 즉시 발행 (이메일 미발송)
  python scripts/publish_weekly_to_substack.py --issue 1 --date 2026-05-11 --publish

  # Draft 생성 + 발행 + 구독자 이메일 발송
  python scripts/publish_weekly_to_substack.py --issue 1 --date 2026-05-11 --publish --send-email

  # 특정 signal ID 지정
  python scripts/publish_weekly_to_substack.py --issue 1 --signal-ids 10 11 12 --publish
"""
import argparse
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from dotenv import load_dotenv
from core.database import execute_query
from core.logger import HarnessLogger
from adapters.content.substack_publisher import publish_weekly_issue

load_dotenv()

TOP_SIGNALS_LIMIT = int(os.getenv("SUBSTACK_TOP_SIGNALS", "7"))


def get_top_signals(limit: int = TOP_SIGNALS_LIMIT) -> list[dict]:
    """점수 상위 N개의 refined_output을 가져온다."""
    rows = execute_query("""
        SELECT ro.id, ro.final_title, ro.final_body, ro.tags,
               fs.score, fs.source
        FROM refined_outputs ro
        JOIN filtered_signals fs ON ro.filtered_signal_id = fs.id
        ORDER BY fs.score DESC, ro.created_at DESC
        LIMIT %s
    """, (limit,), fetch=True)
    return [dict(r) for r in rows] if rows else []


def get_signals_by_ids(ids: list[int]) -> list[dict]:
    placeholders = ",".join("%s" for _ in ids)
    rows = execute_query(f"""
        SELECT ro.id, ro.final_title, ro.final_body, ro.tags,
               fs.score, fs.source
        FROM refined_outputs ro
        JOIN filtered_signals fs ON ro.filtered_signal_id = fs.id
        WHERE ro.id IN ({placeholders})
        ORDER BY fs.score DESC
    """, tuple(ids), fetch=True)
    return [dict(r) for r in rows] if rows else []


def parse_body(row: dict) -> dict:
    """final_body가 JSON이면 파싱, 아니면 기본 구조로 감싸기"""
    body = row.get("final_body") or ""
    if isinstance(body, dict):
        return body
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return {
            "final_title": row.get("final_title", ""),
            "hook": "",
            "what_happened": body,
            "why_it_matters": "",
            "quantitative_snapshot": None,
            "korea_implication": "",
            "risk_counterargument": "",
            "watchlist": [],
            "decision_block": {},
        }


def save_issue_to_db(
    issue_number: int,
    issue_date: str,
    signal_ids: list[int],
    substack_url: str,
    status: str,
):
    execute_query("""
        INSERT INTO newsletter_issues
            (issue_date, title, status, source_signal_ids, publishing_platform, public_url)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (
        issue_date,
        f"Physical AI Weekly #{issue_number:03d}",
        status,
        json.dumps(signal_ids),
        "substack",
        substack_url,
    ))


def main():
    parser = argparse.ArgumentParser(description="Substack Weekly Issue 발행")
    parser.add_argument("--issue", type=int, required=True, help="이슈 번호 (예: 1)")
    parser.add_argument("--date", type=str, default=str(date.today()), help="발행일 YYYY-MM-DD")
    parser.add_argument("--signal-ids", type=int, nargs="+", help="특정 refined_output ID 지정")
    parser.add_argument("--top", type=int, default=TOP_SIGNALS_LIMIT, help="상위 N개 자동 선택")
    parser.add_argument("--publish", action="store_true", help="Draft 생성 후 즉시 발행")
    parser.add_argument("--send-email", action="store_true", help="구독자 이메일 발송 (--publish 필요)")
    args = parser.parse_args()

    logger = HarnessLogger(tier=4, correlation_id=f"substack-{args.issue:03d}")

    if not os.getenv("SUBSTACK_SESSION_TOKEN"):
        logger.error("SUBSTACK_SESSION_TOKEN 미설정. .env에 추가 후 재실행하세요.")
        logger.error("  방법: Chrome → Substack 로그인 → F12 → Application → Cookies → substack.sid")
        sys.exit(1)

    # Signal 수집
    if args.signal_ids:
        raw_rows = get_signals_by_ids(args.signal_ids)
    else:
        raw_rows = get_top_signals(args.top)

    if not raw_rows:
        logger.error("발행할 signal이 없습니다. 파이프라인을 먼저 실행하세요.")
        sys.exit(1)

    # final_body JSON 파싱
    signals = [parse_body(r) for r in raw_rows]
    signal_ids = [r["id"] for r in raw_rows]

    logger.info(f"발행 대상 signal {len(signals)}개: {[s['final_title'][:30] for s in signals]}")

    result = publish_weekly_issue(
        signals=signals,
        issue_number=args.issue,
        issue_date=args.date,
        publish=args.publish,
        send_email=args.send_email,
        correlation_id=f"substack-{args.issue:03d}",
    )

    if result:
        status = "published" if args.publish else "draft"
        save_issue_to_db(args.issue, args.date, signal_ids, result.get("url", ""), status)
        print(f"\n✅ 완료!")
        print(f"   Status : {result.get('status')}")
        print(f"   URL    : {result.get('url', '(draft - Substack 대시보드에서 확인)')}")
        print(f"   Issue  : Physical AI Weekly #{args.issue:03d}")
    else:
        print("\n❌ 발행 실패. 로그를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
