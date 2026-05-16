#!/bin/sh
set -eu

PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

OPENCLAW_BIN="${OPENCLAW_BIN:-openclaw}"

JOB_NAME="harness-weekly-competitor-benchmark"
JOB_MESSAGE='Use the harness-control skill, then run `GEMINI_CLI_TRUST_WORKSPACE=true .venv/bin/python scripts/openclaw_codex_bridge.py dispatch-task-packet benchmark "Competitor report benchmark" --objective "Compare world-class paid AI and tech intelligence report products, extract differentiators, and identify monetizable gaps for Harness." --input-artifact docs/COMPETITIVE_LANDSCAPE.md --input-artifact docs/MONETIZATION_STRATEGY.md --output-artifact docs/reports/COMPETITOR_BENCHMARK_ROUND1.md --check "Cite only information from provided materials or explicitly marked assumptions." --check "Flag risks if the proposed product is below premium benchmark quality." --provider claude --provider gemini --provider copilot` . Return only a short confirmation with packet path and all provider output paths.'

register_if_missing() {
  NAME="$1"
  shift
  if "$OPENCLAW_BIN" cron list --json | grep -q "\"name\":\"$NAME\""; then
    echo "exists: $NAME"
  else
    "$OPENCLAW_BIN" cron add "$@" --json
  fi
}

JOB_IDS=$("$OPENCLAW_BIN" cron list --json | python3 -c '
import json, sys
data = json.load(sys.stdin)
for job in data.get("jobs", []):
    if job.get("name") == "harness-weekly-competitor-benchmark":
        print(job["id"])
')

if [ -n "$JOB_IDS" ]; then
  FIRST_JOB_ID=$(printf "%s\n" "$JOB_IDS" | head -n 1)
  "$OPENCLAW_BIN" cron edit "$FIRST_JOB_ID" \
    --message "$JOB_MESSAGE" \
    --timeout-seconds 420 \
    --no-deliver >/dev/null
  printf "%s\n" "$JOB_IDS" | tail -n +2 | while IFS= read -r EXTRA_JOB_ID; do
    [ -n "$EXTRA_JOB_ID" ] || continue
    "$OPENCLAW_BIN" cron edit "$EXTRA_JOB_ID" --disable >/dev/null
  done
else
  register_if_missing \
    "$JOB_NAME" \
    --name "$JOB_NAME" \
    --description "Weekly competitor benchmark refresh via OpenClaw and Gemini CLI on the 24/7 host." \
    --cron "15 10 * * 1" \
    --tz "Asia/Seoul" \
    --agent main \
    --session isolated \
    --message "$JOB_MESSAGE" \
    --timeout-seconds 420 \
    --no-deliver \
    --wake now
fi

"$OPENCLAW_BIN" cron list --json
