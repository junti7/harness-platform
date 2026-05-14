#!/bin/bash
# T-17: harness_prod 일일 백업
# 보존: 일별 7개 / 주별 4개 / 월별 12개

set -euo pipefail

BACKUP_DIR="${HOME}/harness_backups"
DB_NAME="harness_prod"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")
DAY_OF_WEEK=$(date +"%u")   # 1=Mon 7=Sun
DAY_OF_MONTH=$(date +"%d")

mkdir -p "${BACKUP_DIR}/daily"
mkdir -p "${BACKUP_DIR}/weekly"
mkdir -p "${BACKUP_DIR}/monthly"

# ── 일별 덤프 ────────────────────────────────────────────────────────────────
DAILY_FILE="${BACKUP_DIR}/daily/${DB_NAME}_${TIMESTAMP}.sql.gz"
echo "[backup] pg_dump → ${DAILY_FILE}"
pg_dump "${DB_NAME}" | gzip > "${DAILY_FILE}"
echo "[backup] 완료: $(du -sh "${DAILY_FILE}" | cut -f1)"

# ── 주별 복사 (매주 일요일) ──────────────────────────────────────────────────
if [ "${DAY_OF_WEEK}" = "7" ]; then
    WEEKLY_FILE="${BACKUP_DIR}/weekly/${DB_NAME}_week_${TIMESTAMP}.sql.gz"
    cp "${DAILY_FILE}" "${WEEKLY_FILE}"
    echo "[backup] 주별 백업 저장: ${WEEKLY_FILE}"
fi

# ── 월별 복사 (매달 1일) ────────────────────────────────────────────────────
if [ "${DAY_OF_MONTH}" = "01" ]; then
    MONTHLY_FILE="${BACKUP_DIR}/monthly/${DB_NAME}_month_${TIMESTAMP}.sql.gz"
    cp "${DAILY_FILE}" "${MONTHLY_FILE}"
    echo "[backup] 월별 백업 저장: ${MONTHLY_FILE}"
fi

# ── 보존 정책 적용 ────────────────────────────────────────────────────────────
# 일별: 7개 초과 삭제
find "${BACKUP_DIR}/daily" -name "*.sql.gz" -type f | \
    sort -r | tail -n +8 | xargs -r rm -v

# 주별: 4개 초과 삭제
find "${BACKUP_DIR}/weekly" -name "*.sql.gz" -type f | \
    sort -r | tail -n +5 | xargs -r rm -v

# 월별: 12개 초과 삭제
find "${BACKUP_DIR}/monthly" -name "*.sql.gz" -type f | \
    sort -r | tail -n +13 | xargs -r rm -v

echo "[backup] 보존 정책 적용 완료"
ls -lh "${BACKUP_DIR}/daily/" | tail -5

# ── MBP rsync (선택) ─────────────────────────────────────────────────────────
if [ -n "${BACKUP_RSYNC_TARGET:-}" ]; then
    rsync -az "${BACKUP_DIR}/" "${BACKUP_RSYNC_TARGET}/" \
        && echo "[backup] MBP rsync 완료" \
        || echo "[backup] MBP rsync 실패 (무시)"
fi
