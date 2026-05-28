#!/usr/bin/env bash
# OpenClaw 게이트웨이 워치독
# Mac Mini LaunchAgent에서 120초마다 실행.
# 프로세스가 죽었거나 게이트웨이 응답이 없으면 launchctl로 재시동.

set -euo pipefail

LABEL="${OPENCLAW_LAUNCHAGENT_LABEL:-ai.openclaw.gateway}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
LOG_DIR="${HOME}/.openclaw/watchdog"
LOG_FILE="${LOG_DIR}/watchdog.log"

mkdir -p "$LOG_DIR"

ts() { date '+%Y-%m-%dT%H:%M:%S'; }

log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

# 오래된 로그 정리 (7일 초과 줄 제거)
if [[ -f "$LOG_FILE" ]]; then
    tail -n 5000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

# 1. 프로세스 체크
PID=$(pgrep -f "openclaw.*gateway" 2>/dev/null | head -1 || true)

# 2. 게이트웨이 HTTP 체크
GATEWAY_OK=0
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "http://127.0.0.1:${PORT}/" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" != "000" && "$HTTP_CODE" -lt 500 ]]; then
    GATEWAY_OK=1
fi

if [[ -n "$PID" && "$GATEWAY_OK" -eq 1 ]]; then
    log "OK pid=${PID} gateway=reachable(${HTTP_CODE})"
    exit 0
fi

# 죽었거나 응답 없음 → 재시동
UID_VAL=$(id -u)
log "DEAD pid=${PID:-none} gateway=${HTTP_CODE} → kickstart ${LABEL}"

if launchctl kickstart -k "gui/${UID_VAL}/${LABEL}" 2>>"$LOG_FILE"; then
    log "kickstart 완료 - 3초 대기 후 재검증"
    sleep 3
    NEW_PID=$(pgrep -f "openclaw.*gateway" 2>/dev/null | head -1 || true)
    NEW_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 --max-time 5 "http://127.0.0.1:${PORT}/" 2>/dev/null || echo "000")
    log "재시동 결과: pid=${NEW_PID:-none} gateway=${NEW_HTTP}"
else
    log "kickstart 실패 - launchagent 미설치 가능. 직접 실행 시도"
    OPENCLAW_BIN="${OPENCLAW_BIN:-/opt/homebrew/bin/openclaw}"
    if [[ -x "$OPENCLAW_BIN" ]]; then
        pkill -f "openclaw.*gateway" 2>/dev/null || true
        sleep 1
        nohup "$OPENCLAW_BIN" gateway --port "$PORT" >> "${LOG_DIR}/gateway.log" 2>&1 &
        log "직접 실행 완료 (nohup)"
    else
        log "CRITICAL: openclaw 바이너리 없음 (${OPENCLAW_BIN})"
        exit 1
    fi
fi
