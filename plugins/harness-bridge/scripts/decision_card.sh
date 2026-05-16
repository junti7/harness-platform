#!/bin/sh
set -eu
if [ "$#" -lt 2 ]; then
  echo "usage: decision_card.sh <target_type> <target_id> [format]" >&2
  exit 1
fi
FORMAT="${3:-json}"
cd "$HOME/projects/harness-platform"
.venv/bin/python scripts/openclaw_codex_bridge.py decision-card "$1" "$2" --format "$FORMAT"
