#!/bin/sh
set -eu
if [ "$#" -lt 2 ]; then
  echo "usage: route_note.sh <route> <text>" >&2
  exit 1
fi
cd "$HOME/projects/harness-platform"
.venv/bin/python scripts/openclaw_codex_bridge.py route-note "$1" "$2"
