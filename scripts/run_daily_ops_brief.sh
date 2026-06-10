#!/bin/bash
# 일일 마감 작업 파이프라인 (정밀도 오디트 + Ops Brief)
set -uo pipefail

PROJECT_DIR="/Users/juntaepark/projects/harness-platform"
cd "$PROJECT_DIR"

echo "=== [1/3] 가격 피드 정밀도 오디트 실행 ==="
.venv/bin/python scripts/audit_price_feed_precision.py > docs/reports/price_feed_audit.txt 2>&1 || true

echo "=== [2/3] 오디트 결과 Slack 업로드 ==="
if [ -f docs/reports/price_feed_audit.txt ]; then
  .venv/bin/python scripts/send_slack_file.py \
    docs/reports/price_feed_audit.txt \
    --route exec_daily_brief \
    --title "가격 피드 정밀도 오디트 보고서" \
    --comment "Alpaca vs Yahoo 가격 피드 오디트 결과입니다." || true
fi

echo "=== [3/3] 일일 자동화 ops brief 실행 ==="
.venv/bin/python3 scripts/openclaw_ops_sync.py \
  --to-slack \
  --to-notion \
  --route exec_daily_brief \
  --summary-text "Daily automated ops brief (launchd direct — no LLM overhead)" \
  --review-type openclaw_daily_ops
