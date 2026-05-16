#!/bin/sh
set -eu
if [ "$#" -lt 4 ]; then
  echo "usage: record_decision.sh <target_type> <target_id> <decision> <approval_type> [reason]" >&2
  exit 1
fi
cd "$HOME/projects/harness-platform"
if [ "$#" -ge 5 ]; then
  .venv/bin/python scripts/openclaw_codex_bridge.py record-decision "$1" "$2" "$3" "$4" --reason "$5"
else
  .venv/bin/python scripts/openclaw_codex_bridge.py record-decision "$1" "$2" "$3" "$4"
fi
