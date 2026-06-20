#!/bin/sh
set -eu

# 런타임 의존성(프로비저닝 주의):
#   com.harness.harness-os-frontend 는 프로덕션 정적 서버로 전역 `serve` 바이너리
#   (/opt/homebrew/bin/serve)를 사용한다(빌드된 dist 서빙; vite dev 아님).
#   미설치 시 프론트 agent 가 crash-loop 하므로 새/복구 머신에서는 먼저:  npm i -g serve
#   (scripts/deploy_to_macmini.sh 의 plist reload 단계도 존재를 preflight 검증한다.)

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PLIST_DIR="$ROOT/harness-os/launchd"
AGENT_DIR="$HOME/Library/LaunchAgents"

if [ ! -x /opt/homebrew/bin/serve ]; then
  echo "⚠️  /opt/homebrew/bin/serve 없음 — 프론트(serve dist) agent 가 crash-loop 합니다. 'npm i -g serve' 후 재실행 권장." >&2
fi

mkdir -p "$AGENT_DIR"

for name in \
  com.harness.pipeline \
  com.harness.harness-os-backend \
  com.harness.harness-os-frontend \
  com.harness.maily-metrics-sync \
  com.harness.tier2-filter \
  com.harness.tier2-filter-fast \
  com.harness.tier3-filter \
  com.harness.daily-news-pdf \
  com.harness.pipeline-watchdog \
  com.harness.ibkr-watchdog \
  com.harness.turtle-auto-trader \
  com.harness.ibkr-auto-trader \
  com.harness.paper-reset-watch \
  com.harness.trading-runtime-guard \
  com.harness.post-open-verification; do
  src="$PLIST_DIR/$name.plist"
  dst="$AGENT_DIR/$name.plist"
  sed "s|__ROOT__|$ROOT|g" "$src" >"$dst"
  launchctl unload "$dst" >/dev/null 2>&1 || true
  launchctl load "$dst"
  echo "loaded: $name"
done

legacy_backend="$AGENT_DIR/com.harness.backend.plist"
if [ -f "$legacy_backend" ]; then
  launchctl unload "$legacy_backend" >/dev/null 2>&1 || true
  rm -f "$legacy_backend"
  echo "removed: com.harness.backend (legacy)"
fi

echo "Harness-OS launchd services registered."
