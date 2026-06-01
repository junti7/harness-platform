#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PLIST_DIR="$ROOT/harness-os/launchd"
AGENT_DIR="$HOME/Library/LaunchAgents"

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
  com.harness.ibkr-watchdog; do
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
