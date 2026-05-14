#!/bin/bash
# T-17: harness_prod 복구 절차
# 사용법: ./infra/restore_db.sh ~/harness_backups/daily/harness_prod_2026-05-14_030000.sql.gz

set -euo pipefail

BACKUP_FILE="${1:-}"
DB_NAME="harness_prod"
RESTORE_DB="${2:-harness_prod_restore}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "사용법: $0 <백업파일.sql.gz> [복구DB명]"
    echo ""
    echo "최근 백업 목록:"
    ls -lht "${HOME}/harness_backups/daily/" 2>/dev/null | head -5
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "오류: 파일 없음 — ${BACKUP_FILE}"
    exit 1
fi

echo "[restore] 백업: ${BACKUP_FILE}"
echo "[restore] 복구 DB: ${RESTORE_DB}"
echo ""
echo "⚠️  복구 전 확인:"
echo "   - 기존 ${RESTORE_DB} DB는 DROP/CREATE됩니다"
echo "   - harness_prod에 직접 복구하려면 RESTORE_DB=harness_prod로 재실행하세요"
echo ""
read -p "계속하시겠습니까? (yes/no): " confirm
[ "${confirm}" = "yes" ] || { echo "취소됨"; exit 0; }

# DB 재생성
psql -c "DROP DATABASE IF EXISTS \"${RESTORE_DB}\";" postgres
psql -c "CREATE DATABASE \"${RESTORE_DB}\";" postgres

# 복구
echo "[restore] 복구 중..."
gunzip -c "${BACKUP_FILE}" | psql "${RESTORE_DB}"

echo ""
echo "✅ 복구 완료: ${RESTORE_DB}"
echo "   테이블 수: $(psql -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" "${RESTORE_DB}")"
