#!/bin/sh
set -eu

# Ensure Homebrew prefix is available even in non-login shells (e.g. SSH, launchd).
# Some environments provide a minimal PATH like /usr/bin:/bin which hides /opt/homebrew/bin.
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

if [ -z "${OPENCLAW_BIN:-}" ]; then
  if [ -x "/opt/homebrew/bin/openclaw" ]; then
    OPENCLAW_BIN="/opt/homebrew/bin/openclaw"
  else
    OPENCLAW_BIN="openclaw"
  fi
fi

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

get_job_id() {
  NAME="$1"
  "$OPENCLAW_BIN" cron list --json | python3 -c 'import json,sys; name=sys.argv[1]; jobs=json.load(sys.stdin).get("jobs", []); hit=[j for j in jobs if j.get("name")==name]; print(hit[0].get("id","") if hit else "")' "$NAME"
}

ensure_cron_schedule() {
  NAME="$1"
  CRON_EXPR="$2"
  TZ="$3"

  JOB_ID="$(get_job_id "$NAME")"
  if [ -z "$JOB_ID" ]; then
    return 0
  fi

  # `openclaw cron get` already returns JSON to stdout.
  CURRENT="$("$OPENCLAW_BIN" cron get "$JOB_ID" | python3 -c 'import json,sys; job=json.load(sys.stdin); sch=(job.get("schedule") or {}); print((sch.get("expr") or "") + "|" + (sch.get("tz") or ""))')"
  CUR_EXPR="${CURRENT%%|*}"
  CUR_TZ="${CURRENT#*|}"

  if [ "$CUR_EXPR" = "$CRON_EXPR" ] && [ "$CUR_TZ" = "$TZ" ]; then
    echo "schedule ok: $NAME ($CRON_EXPR $TZ)"
    return 0
  fi

  echo "schedule update: $NAME ($CUR_EXPR $CUR_TZ) -> ($CRON_EXPR $TZ)"
  "$OPENCLAW_BIN" cron edit "$JOB_ID" --cron "$CRON_EXPR" --tz "$TZ" --json >/dev/null
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
  --cron "30 4 * * *" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --message "$DAILY_MESSAGE" \
  --timeout-seconds 300 \
  --no-deliver \
  --wake now

ensure_cron_schedule "$DAILY_NAME" "30 4 * * *" "Asia/Seoul"

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
