#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

CEO_PW="${1:-ceo123}"
VP_PW="${2:-vp123}"

echo "=== 비밀번호 초기화 ==="

if [ ! -f "$ENV_FILE" ]; then
  touch "$ENV_FILE"
fi

# 기존 값 교체, 없으면 추가
if grep -q "^HARNESS_CEO_PASSWORD=" "$ENV_FILE"; then
  sed -i '' "s/^HARNESS_CEO_PASSWORD=.*/HARNESS_CEO_PASSWORD=${CEO_PW}/" "$ENV_FILE"
else
  echo "HARNESS_CEO_PASSWORD=${CEO_PW}" >> "$ENV_FILE"
fi

if grep -q "^HARNESS_VP_PASSWORD=" "$ENV_FILE"; then
  sed -i '' "s/^HARNESS_VP_PASSWORD=.*/HARNESS_VP_PASSWORD=${VP_PW}/" "$ENV_FILE"
else
  echo "HARNESS_VP_PASSWORD=${VP_PW}" >> "$ENV_FILE"
fi

echo "CEO 비밀번호: ${CEO_PW}"
echo "VP  비밀번호: ${VP_PW}"

echo "=== 백엔드 재시동 ==="
launchctl kickstart -k "gui/$(id -u)/com.harness.backend" && echo "재시동 완료" || echo "재시동 실패 - 수동 확인 필요"

echo ""
echo "✅ 완료. 위 비밀번호로 로그인하세요."
