#!/bin/sh
set -eu

ROOT="/Users/juntae.park/projects/harness-platform"
VENV_PY="$ROOT/.venv/bin/python"
SCRIPT="$ROOT/scripts/sync_maily_metrics.py"
CSV_PATH="${MAILY_METRICS_CSV_PATH:-}"

if [ ! -x "$VENV_PY" ]; then
  echo "missing python: $VENV_PY" >&2
  exit 1
fi

if [ -z "$CSV_PATH" ]; then
  echo "MAILY_METRICS_CSV_PATH is not set" >&2
  exit 1
fi

if [ ! -f "$CSV_PATH" ]; then
  echo "maily csv not found: $CSV_PATH" >&2
  exit 1
fi

cd "$ROOT"
exec "$VENV_PY" "$SCRIPT" --csv "$CSV_PATH"
