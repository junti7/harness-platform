"""
QA Check CLI

사용법:
  # newsletter_issue QA
  python scripts/run_qa_check.py --issue-id 1

  # refined_output QA
  python scripts/run_qa_check.py --refined-output-id 42

  # newsletter_issue의 각 signal에 개별 QA 후 issue 전체 QA
  python scripts/run_qa_check.py --issue-id 1 --batch-signals

종료 코드:
  0 = QA 통과 (qa_clear = approved)
  1 = QA 실패 (rejected) 또는 오류
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from core.database import execute_query
from adapters.content.qa_agent import (
    qa_check_newsletter_issue,
    qa_check_refined_output,
    has_qa_clear,
)

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Harness QA Gate")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--issue-id", type=int, help="newsletter_issues.id")
    group.add_argument("--refined-output-id", type=int, help="refined_outputs.id")
    parser.add_argument(
        "--batch-signals", action="store_true",
        help="issue의 각 signal에 대해 refined_output QA도 개별 실행",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="이미 qa_clear approved인 경우도 재실행",
    )
    args = parser.parse_args()

    if args.refined_output_id:
        ro_id = args.refined_output_id
        if not args.force and has_qa_clear(ro_id):
            print(f"[QA] refined_output#{ro_id}: 이미 approved — 스킵 (--force로 재실행)")
            sys.exit(0)
        approved = qa_check_refined_output(ro_id)
        sys.exit(0 if approved else 1)

    # newsletter_issue
    issue_id = args.issue_id
    if not args.force and has_qa_clear(issue_id):
        print(f"[QA] newsletter_issue#{issue_id}: 이미 approved — 스킵 (--force로 재실행)")
        sys.exit(0)

    if args.batch_signals:
        rows = execute_query(
            "SELECT source_signal_ids FROM newsletter_issues WHERE id = %s",
            (issue_id,), fetch=True,
        )
        if rows:
            raw = rows[0]["source_signal_ids"] or "[]"
            signal_ids = raw if isinstance(raw, list) else json.loads(raw)
            all_passed = True
            for sid in signal_ids:
                ok = qa_check_refined_output(sid)
                status = "✅" if ok else "❌"
                print(f"  {status} signal#{sid}")
                if not ok:
                    all_passed = False
            if not all_passed:
                print("[QA] 일부 signal QA 실패")
                sys.exit(1)

    approved = qa_check_newsletter_issue(issue_id)
    sys.exit(0 if approved else 1)


if __name__ == "__main__":
    main()
