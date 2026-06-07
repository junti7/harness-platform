#!/usr/bin/env bash
# 2026 AI 글로벌 수집 데몬(launchd) 설치/재설치 — 머신 경로 자동 치환.
#
# 재발 방지: plist에 절대경로를 하드코딩하면 MBP↔Mac Mini 동기화 시 경로가 깨진다
# (2026-06-03 사고: MBP 경로 plist가 Mac Mini에 설치돼 exit 78로 4일간 수집 중단).
# 이 스크립트는 템플릿의 __PROJECT_ROOT__ 를 '실행 중인 머신의 실제 repo 경로'로 채워 설치한다.
#
# 사용: bash scripts/install_gather_daemon.sh        (설치/재설치 + 재적재)
#       bash scripts/install_gather_daemon.sh --status (상태만)
set -euo pipefail

LABEL="com.harness.2026-ai-seamless-gather"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/launchd/$LABEL.plist"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [ "${1:-}" = "--status" ]; then
  launchctl list | grep "$LABEL" || echo "미등록"
  exit 0
fi

[ -f "$TEMPLATE" ] || { echo "❌ 템플릿 없음: $TEMPLATE"; exit 1; }
mkdir -p "$HOME/Library/LaunchAgents"

# __PROJECT_ROOT__ placeholder + 혹시 남아있을 절대경로까지 현재 ROOT로 치환
sed -e "s|__PROJECT_ROOT__|$ROOT|g" \
    -e "s|/Users/[^/]*/projects/harness-platform|$ROOT|g" \
    "$TEMPLATE" > "$DEST"

plutil -lint "$DEST" >/dev/null || { echo "❌ plist 문법 오류"; exit 1; }

PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || echo "⚠️  경고: venv python 없음($PY) — 데몬이 실패할 수 있음"

launchctl unload "$DEST" 2>/dev/null || true
launchctl load "$DEST"
echo "✅ 설치 완료: $DEST"
echo "   ROOT=$ROOT"
launchctl list | grep "$LABEL" || true
