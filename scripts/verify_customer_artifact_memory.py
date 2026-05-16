import argparse
from typing import Any

from core.database import execute_query


def load_usage(artifact_type: str, artifact_id: int) -> dict[str, Any]:
    rows = execute_query(
        """
        SELECT
            amu.*,
            cp.external_ref,
            cp.consent_personalization
        FROM artifact_memory_usage amu
        LEFT JOIN customer_profiles cp
            ON cp.id = amu.customer_id
        WHERE amu.artifact_type = %s AND amu.artifact_id = %s
        ORDER BY amu.id DESC
        LIMIT 1
        """,
        (artifact_type, artifact_id),
        fetch=True,
    )
    if not rows:
        raise RuntimeError(f"artifact_memory_usage not found for {artifact_type}#{artifact_id}")
    return rows[0]


def verify_usage(row: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []

    if row.get("audience_scope") == "individual":
        if not row.get("customer_id"):
            issues.append("individual artifact인데 customer_id가 없음")
        if not row.get("consent_personalization"):
            issues.append("개인화 동의 없는 고객 데이터 사용")

    if not row.get("usage_summary"):
        issues.append("usage_summary 없음")

    if len(row.get("memory_event_ids") or []) == 0:
        issues.append("memory_event_ids 비어 있음")
    if len(row.get("watchlist_ids") or []) == 0:
        issues.append("watchlist_ids 비어 있음")
    if len(row.get("question_ids") or []) == 0:
        issues.append("question_ids 비어 있음")

    return (len(issues) == 0, issues)


def mark_pass(artifact_type: str, artifact_id: int, reason: str) -> None:
    execute_query(
        """
        UPDATE artifact_memory_usage
        SET qa_checked = TRUE
        WHERE artifact_type = %s AND artifact_id = %s
        """,
        (artifact_type, artifact_id),
    )
    execute_query(
        """
        INSERT INTO ceo_decisions (target_type, target_id, decision, approval_type, reason, decided_by)
        VALUES (%s, %s, 'approved', 'qa_clear', %s, 'QA Agent')
        ON CONFLICT (target_type, target_id, decision)
        DO UPDATE SET
            approval_type = EXCLUDED.approval_type,
            reason = EXCLUDED.reason,
            decided_by = EXCLUDED.decided_by
        """,
        (artifact_type, artifact_id, reason),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify artifact_memory_usage and mark qa_checked.")
    parser.add_argument("artifact_type")
    parser.add_argument("artifact_id", type=int)
    args = parser.parse_args()

    row = load_usage(args.artifact_type, args.artifact_id)
    ok, issues = verify_usage(row)
    if not ok:
        for issue in issues:
            print(f"BLOCK: {issue}")
        return 1

    reason = (
        f"memory={len(row.get('memory_event_ids') or [])}, "
        f"overrides={len(row.get('override_ids') or [])}, "
        f"watchlists={len(row.get('watchlist_ids') or [])}, "
        f"questions={len(row.get('question_ids') or [])}"
    )
    mark_pass(args.artifact_type, args.artifact_id, reason)
    print(f"QA CLEAR: {args.artifact_type}#{args.artifact_id} | {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
