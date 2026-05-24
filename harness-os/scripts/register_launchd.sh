#!/bin/sh
set -eu

ROOT="/Users/juntae.park/projects/harness-platform"
PLIST_DIR="$ROOT/harness-os/launchd"
AGENT_DIR="$HOME/Library/LaunchAgents"

mkdir -p "$AGENT_DIR"

for name in \
  com.harness.harness-os-backend \
  com.harness.harness-os-frontend \
  com.harness.maily-metrics-sync; do
  src="$PLIST_DIR/$name.plist"
  dst="$AGENT_DIR/$name.plist"
  cp "$src" "$dst"
  launchctl unload "$dst" >/dev/null 2>&1 || true
  launchctl load "$dst"
  echo "loaded: $name"
done

echo "Harness-OS launchd services registered."
