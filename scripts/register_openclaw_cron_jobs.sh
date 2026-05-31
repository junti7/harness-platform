#!/bin/sh
set -eu

# Ensure Homebrew prefix is available even in non-login shells (e.g. SSH, launchd).
# Some environments provide a minimal PATH like /usr/bin:/bin which hides /opt/homebrew/bin.
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
OPENCLAW_CRON_MODEL="ollama/gemma4:latest"

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
DAILY_MESSAGE='Run exactly this command from /Users/juntaepark/projects/harness-platform: /Users/juntaepark/projects/harness-platform/.venv/bin/python /Users/juntaepark/projects/harness-platform/scripts/openclaw_codex_bridge.py publish-ops-brief --to-slack --to-notion --route exec_daily_brief --summary-text "daily ops automated check" . After the command completes, reply with exactly OK.'

WEEKLY_RED_TEAM_NAME="harness-weekly-multi-llm-red-team"
WEEKLY_RED_TEAM_MESSAGE='Run exactly this command from /Users/juntaepark/projects/harness-platform and return only its stdout: DATABASE_URL=postgresql://localhost/harness_prod PYTHONPYCACHEPREFIX=/private/tmp /Users/juntaepark/projects/harness-platform/.venv/bin/python /Users/juntaepark/projects/harness-platform/scripts/run_weekly_red_team_latest.py'

GMAIL_CHECK_NAME="harness-gmail-ops-check"
GMAIL_CHECK_MESSAGE='Run exactly this command from /Users/juntaepark/projects/harness-platform: /Users/juntaepark/projects/harness-platform/.venv/bin/python /Users/juntaepark/projects/harness-platform/scripts/run_gmail_ops_check.py --query newer_than:1d --limit 10 --route exec_president_decisions . After the command completes, reply with exactly OK.'

GOAL_SNAPSHOT_NAME="harness-daily-goal-snapshot"
GOAL_SNAPSHOT_MESSAGE='Run exactly these commands from /Users/juntaepark/projects/harness-platform: /Users/juntaepark/projects/harness-platform/.venv/bin/python /Users/juntaepark/projects/harness-platform/scripts/bootstrap_default_goals.py && /Users/juntaepark/projects/harness-platform/.venv/bin/python /Users/juntaepark/projects/harness-platform/scripts/run_goal_snapshot.py . After the commands complete, reply with exactly OK.'

CONFERENCE_AUDIT_NAME="harness-weekly-conference-room-audit"
CONFERENCE_AUDIT_MESSAGE='Run exactly this command from /Users/juntaepark/projects/harness-platform: python3 /Users/juntaepark/projects/harness-platform/scripts/summarize_conference_room_audit.py --limit 500 --to-slack --route exec_president_decisions . After the command completes, reply with exactly OK.'

ROUTE_AUDIT_NAME="harness-weekly-route-audit"
ROUTE_AUDIT_MESSAGE='Run exactly this command from /Users/juntaepark/projects/harness-platform: /Users/juntaepark/projects/harness-platform/.venv/bin/python /Users/juntaepark/projects/harness-platform/scripts/summarize_openclaw_route_audit.py --limit 500 --change-date 2026-05-31 --to-slack --route exec_president_decisions . After the command completes, reply with exactly OK.'

TOPIC_REFRESH_NAME="harness-topic-registry-refresh"
TOPIC_REFRESH_MESSAGE='Run exactly this command from /Users/juntaepark/projects/harness-platform: /Users/juntaepark/projects/harness-platform/.venv/bin/python /Users/juntaepark/projects/harness-platform/scripts/refresh_topic_registry.py . After the command completes, reply with exactly OK.'


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

sync_agent_payload() {
  NAME="$1"
  MESSAGE="$2"
  TIMEOUT="$3"
  MODEL="${4:-}"
  TOOLS="${5:-}"
  LIGHT_CONTEXT="${6:-false}"

  JOB_ID="$(get_job_id "$NAME")"
  if [ -z "$JOB_ID" ]; then
    return 0
  fi

  CURRENT_JSON="$("$OPENCLAW_BIN" cron show "$JOB_ID" --json)"
  CURRENT_MESSAGE="$(printf "%s" "$CURRENT_JSON" | python3 -c 'import json,sys; job=json.load(sys.stdin); print(((job.get("payload") or {}).get("message") or ""))')"
  CURRENT_TIMEOUT="$(printf "%s" "$CURRENT_JSON" | python3 -c 'import json,sys; job=json.load(sys.stdin); print(int(((job.get("payload") or {}).get("timeoutSeconds") or 0)))')"
  CURRENT_MODEL="$(printf "%s" "$CURRENT_JSON" | python3 -c 'import json,sys; job=json.load(sys.stdin); print(((job.get("payload") or {}).get("model") or ""))')"
  CURRENT_TOOLS="$(printf "%s" "$CURRENT_JSON" | python3 -c 'import json,sys; job=json.load(sys.stdin); tools=((job.get("payload") or {}).get("toolsAllow") or []); print(",".join(tools))')"
  CURRENT_LIGHT_CONTEXT="$(printf "%s" "$CURRENT_JSON" | python3 -c 'import json,sys; job=json.load(sys.stdin); print(str(bool((job.get("payload") or {}).get("lightContext", False))).lower())')"

  if [ "$CURRENT_MESSAGE" = "$MESSAGE" ] \
    && [ "$CURRENT_TIMEOUT" = "$TIMEOUT" ] \
    && [ "$CURRENT_MODEL" = "$MODEL" ] \
    && [ "$CURRENT_TOOLS" = "$TOOLS" ] \
    && [ "$CURRENT_LIGHT_CONTEXT" = "$LIGHT_CONTEXT" ]; then
    echo "payload ok: $NAME"
    return 0
  fi

  echo "payload update: $NAME"
  set -- "$OPENCLAW_BIN" cron edit "$JOB_ID" --message "$MESSAGE" --timeout-seconds "$TIMEOUT"
  if [ -n "$MODEL" ]; then
    set -- "$@" --model "$MODEL"
  fi
  if [ -n "$TOOLS" ]; then
    set -- "$@" --tools "$TOOLS"
  else
    set -- "$@" --clear-tools
  fi
  if [ "$LIGHT_CONTEXT" = "true" ]; then
    set -- "$@" --light-context
  else
    set -- "$@" --no-light-context
  fi
  "$@" >/dev/null
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
  CURRENT="$("$OPENCLAW_BIN" cron show "$JOB_ID" --json | python3 -c 'import json,sys; job=json.load(sys.stdin); sch=(job.get("schedule") or {}); print((sch.get("expr") or "") + "|" + (sch.get("tz") or ""))')"
  CUR_EXPR="${CURRENT%%|*}"
  CUR_TZ="${CURRENT#*|}"

  if [ "$CUR_EXPR" = "$CRON_EXPR" ] && [ "$CUR_TZ" = "$TZ" ]; then
    echo "schedule ok: $NAME ($CRON_EXPR $TZ)"
    return 0
  fi

  echo "schedule update: $NAME ($CUR_EXPR $CUR_TZ) -> ($CRON_EXPR $TZ)"
  "$OPENCLAW_BIN" cron edit "$JOB_ID" --cron "$CRON_EXPR" --tz "$TZ" >/dev/null
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
  --model "$OPENCLAW_CRON_MODEL" \
  --tools exec \
  --light-context \
  --message "$DAILY_MESSAGE" \
  --timeout-seconds 300 \
  --no-deliver \
  --wake now

ensure_cron_schedule "$DAILY_NAME" "30 4 * * *" "Asia/Seoul"
sync_agent_payload "$DAILY_NAME" "$DAILY_MESSAGE" "300" "$OPENCLAW_CRON_MODEL" "exec" "true"

register_if_missing \
  "$WEEKLY_RED_TEAM_NAME" \
  --name "$WEEKLY_RED_TEAM_NAME" \
  --description "Weekly 3-model red-team governance run for the latest review target." \
  --cron "0 10 * * 1" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --tools exec \
  --light-context \
  --message "$WEEKLY_RED_TEAM_MESSAGE" \
  --timeout-seconds 900 \
  --no-deliver

sync_agent_payload "$WEEKLY_RED_TEAM_NAME" "$WEEKLY_RED_TEAM_MESSAGE" "900" "" "exec" "true"

register_if_missing \
  "$GMAIL_CHECK_NAME" \
  --name "$GMAIL_CHECK_NAME" \
  --description "Check the CEO's Gmail inbox twice daily (05:00 and 14:00 KST) for company management-related emails, summarize them, and report to Slack." \
  --cron "0 5,14 * * *" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --model "$OPENCLAW_CRON_MODEL" \
  --tools exec \
  --light-context \
  --message "$GMAIL_CHECK_MESSAGE" \
  --timeout-seconds 300 \
  --no-deliver

ensure_cron_schedule "$GMAIL_CHECK_NAME" "0 5,14 * * *" "Asia/Seoul"
sync_agent_payload "$GMAIL_CHECK_NAME" "$GMAIL_CHECK_MESSAGE" "300" "$OPENCLAW_CRON_MODEL" "exec" "true"

register_if_missing \
  "$GOAL_SNAPSHOT_NAME" \
  --name "$GOAL_SNAPSHOT_NAME" \
  --description "Bootstrap default strategic goals if missing, then record the daily goal snapshot and pace-based forecast." \
  --cron "20 4 * * *" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --model "$OPENCLAW_CRON_MODEL" \
  --tools exec \
  --light-context \
  --message "$GOAL_SNAPSHOT_MESSAGE" \
  --timeout-seconds 300 \
  --no-deliver

ensure_cron_schedule "$GOAL_SNAPSHOT_NAME" "20 4 * * *" "Asia/Seoul"
sync_agent_payload "$GOAL_SNAPSHOT_NAME" "$GOAL_SNAPSHOT_MESSAGE" "300" "$OPENCLAW_CRON_MODEL" "exec" "true"

register_if_missing \
  "$TOPIC_REFRESH_NAME" \
  --name "$TOPIC_REFRESH_NAME" \
  --description "Refresh active collection topics and generated topic query sources for physical_ai." \
  --cron "0 */6 * * *" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --model "$OPENCLAW_CRON_MODEL" \
  --tools exec \
  --light-context \
  --message "$TOPIC_REFRESH_MESSAGE" \
  --timeout-seconds 240 \
  --no-deliver

ensure_cron_schedule "$TOPIC_REFRESH_NAME" "0 */6 * * *" "Asia/Seoul"
sync_agent_payload "$TOPIC_REFRESH_NAME" "$TOPIC_REFRESH_MESSAGE" "240" "$OPENCLAW_CRON_MODEL" "exec" "true"

register_if_missing \
  "$CONFERENCE_AUDIT_NAME" \
  --name "$CONFERENCE_AUDIT_NAME" \
  --description "Generate the weekly conference-room chatter audit summary for persona length and noise review." \
  --cron "40 3 * * 1" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --model "$OPENCLAW_CRON_MODEL" \
  --tools exec \
  --light-context \
  --message "$CONFERENCE_AUDIT_MESSAGE" \
  --timeout-seconds 300 \
  --no-deliver

ensure_cron_schedule "$CONFERENCE_AUDIT_NAME" "40 3 * * 1" "Asia/Seoul"
sync_agent_payload "$CONFERENCE_AUDIT_NAME" "$CONFERENCE_AUDIT_MESSAGE" "300" "$OPENCLAW_CRON_MODEL" "exec" "true"

register_if_missing \
  "$ROUTE_AUDIT_NAME" \
  --name "$ROUTE_AUDIT_NAME" \
  --description "Generate and send the weekly OpenClaw route audit cost summary." \
  --cron "50 3 * * 1" \
  --tz "Asia/Seoul" \
  --agent main \
  --session isolated \
  --model "$OPENCLAW_CRON_MODEL" \
  --tools exec \
  --light-context \
  --message "$ROUTE_AUDIT_MESSAGE" \
  --timeout-seconds 300 \
  --no-deliver

ensure_cron_schedule "$ROUTE_AUDIT_NAME" "50 3 * * 1" "Asia/Seoul"
sync_agent_payload "$ROUTE_AUDIT_NAME" "$ROUTE_AUDIT_MESSAGE" "300" "$OPENCLAW_CRON_MODEL" "exec" "true"

"$OPENCLAW_BIN" cron list --json
