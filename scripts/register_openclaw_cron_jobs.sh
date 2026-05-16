#!/bin/sh
set -eu

PATH="${PATH:-/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin}"

OPENCLAW_BIN="${OPENCLAW_BIN:-openclaw}"

HEARTBEAT_NAME="harness-control-heartbeat"
HEARTBEAT_MESSAGE='Use the harness-control skill to check the Harness control plane. Return only 5 short bullets: bridge, openclaw, postgres, ollama, slack/notion. If any core dependency is degraded, also run: .venv/bin/python scripts/openclaw_codex_bridge.py publish-ops-brief --to-slack --route ops_incidents --summary-text "<your degraded summary>".'

DAILY_NAME="harness-daily-ops-brief"
DAILY_MESSAGE='Use the harness-control skill to review the Harness control plane. Then run: .venv/bin/python scripts/openclaw_codex_bridge.py publish-ops-brief --to-slack --to-notion --route exec_daily_brief --summary-text "<your concise ops summary>". Return only a short confirmation with health, route, and whether the publish step succeeded.'

WEEKLY_RED_TEAM_NAME="harness-weekly-multi-llm-red-team"
WEEKLY_RED_TEAM_MESSAGE='Use the harness-control skill, then run: DATABASE_URL=postgresql://localhost/harness_prod PYTHONPYCACHEPREFIX=/private/tmp .venv/bin/python scripts/run_weekly_red_team_latest.py. Return only a short confirmation with target, verdict, gate_open, and memo path.'

register_if_missing() {
  NAME="$1"
  shift
  if "$OPENCLAW_BIN" cron list --json | python3 -c 'import json, sys; jobs=json.load(sys.stdin).get("jobs", []); name=sys.argv[1]; raise SystemExit(0 if any(job.get("name")==name for job in jobs) else 1)' "$NAME"; then
    echo "exists: $NAME"
  else
    "$OPENCLAW_BIN" cron add "$@" --json
  fi
}

register_if_missing \
  "$HEARTBEAT_NAME" \
  --name "$HEARTBEAT_NAME" \
  --description "Every 30 minutes, run harness-control via local OpenClaw agent and summarize control-plane readiness." \
  --every 30m \
  --agent main \
  --session isolated \
  --message "$HEARTBEAT_MESSAGE" \
  --timeout-seconds 180 \
  --no-deliver \
  --wake now

register_if_missing \
  "$DAILY_NAME" \
  --name "$DAILY_NAME" \
  --description "Daily operations brief for the Harness 24/7 control plane." \
  --cron "5 9 * * *" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --message "$DAILY_MESSAGE" \
  --timeout-seconds 300 \
  --no-deliver \
  --wake now

register_if_missing \
  "$WEEKLY_RED_TEAM_NAME" \
  --name "$WEEKLY_RED_TEAM_NAME" \
  --description "Weekly 3-model red-team governance run for the latest review target." \
  --cron "0 10 * * 1" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --message "$WEEKLY_RED_TEAM_MESSAGE" \
  --timeout-seconds 900 \
  --no-deliver

"$OPENCLAW_BIN" cron list --json
