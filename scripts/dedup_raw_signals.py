"""
raw_signals 중복 제거 스크립트
- content_hash 기준으로 중복 탐지
- 가장 오래된 행(원본)만 보존, 나머지 삭제
- 삭제 이력을 로그에 기록
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env", override=True)

import psycopg2

LOG_PATH = ROOT / "docs/reports/dedup_log.jsonl"


def run(dry_run: bool = False) -> None:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    # 1. 전체 현황
    cur.execute("SELECT COUNT(*) FROM raw_signals")
    total_before = cur.fetchone()[0]

    # 2. content_hash 기준 중복 탐지 (원본=MIN(id) 보존)
    cur.execute("""
        SELECT content_hash, COUNT(*) as cnt, MIN(id) as keep_id, array_agg(id ORDER BY id) as all_ids
        FROM raw_signals
        WHERE content_hash IS NOT NULL
        GROUP BY content_hash
        HAVING COUNT(*) > 1
    """)
    dup_groups = cur.fetchall()

    delete_ids = []
    for content_hash, cnt, keep_id, all_ids in dup_groups:
        to_delete = [i for i in all_ids if i != keep_id]
        delete_ids.extend(to_delete)

    print(f"전체 레코드: {total_before}건")
    print(f"중복 그룹: {len(dup_groups)}개")
    print(f"삭제 대상: {len(delete_ids)}건 (원본 {len(dup_groups)}건 보존)")

    if not delete_ids:
        print("중복 없음 — 삭제 불필요")
        conn.close()
        return

    if dry_run:
        print("[DRY-RUN] 실제 삭제 미실행")
        # 샘플 출력
        cur.execute(
            "SELECT id, source, ingested_at, raw_data->>'title' FROM raw_signals WHERE id = ANY(%s) LIMIT 5",
            (delete_ids[:5],)
        )
        for row in cur.fetchall():
            print(f"  삭제예정: id={row[0]} [{row[1]}] {str(row[3] or '')[:60]}")
        conn.close()
        return

    # 3. 삭제 실행
    cur.execute("DELETE FROM raw_signals WHERE id = ANY(%s)", (delete_ids,))
    deleted = cur.rowcount
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM raw_signals")
    total_after = cur.fetchone()[0]

    print(f"삭제 완료: {deleted}건 제거 → 잔여 {total_after}건")

    # 4. 로그 기록
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_entry = {
        "event": "dedup_raw_signals",
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "reason": "직접 입력 topic_only 버그로 인한 교육 컨설팅 프리셋 쿼리 혼입 — 중복 제거",
        "total_before": total_before,
        "dup_groups": len(dup_groups),
        "deleted": deleted,
        "total_after": total_after,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    print(f"로그 기록: {LOG_PATH}")

    conn.close()


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    run(dry_run=dry)
