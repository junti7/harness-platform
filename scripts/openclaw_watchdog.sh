#!/usr/bin/env bash
# OpenClaw 게이트웨이 워치독
# Mac Mini LaunchAgent에서 120초마다 실행.
# 프로세스가 죽었거나 게이트웨이 응답이 없으면 launchctl로 재시동.

set -euo pipefail

LABEL="${OPENCLAW_LAUNCHAGENT_LABEL:-ai.openclaw.gateway}"
PORT="${OPENCLAW_GATEWAY_PORT:-18789}"
LOG_DIR="${HOME}/.openclaw/watchdog"
LOG_FILE="${LOG_DIR}/watchdog.log"
HOSTNAME_LC="$(hostname | tr '[:upper:]' '[:lower:]')"

mkdir -p "$LOG_DIR"

ts() { date '+%Y-%m-%dT%H:%M:%S'; }

log() { echo "[$(ts)] $*" | tee -a "$LOG_FILE"; }

if [[ "$HOSTNAME_LC" == *macbook* || "$HOSTNAME_LC" == *mbp* ]]; then
    log "SKIP host=$(hostname) reason=OpenClaw gateway/watchdog is Mac Mini-only"
    exit 0
fi

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
    # 3. 추가 자가 복구: PostgreSQL 데이터베이스 접속 여부 및 harness_dev DB 누락 검사
    DB_VERIFY_OK=1
    DB_STATUS_MSG="OK"
    
    # 3.1 pg_isready 또는 port 5432 listen 상태 체크
    PG_READY_BIN="/opt/homebrew/bin/pg_isready"
    if [[ ! -x "$PG_READY_BIN" ]]; then
        PG_READY_BIN="pg_isready"
    fi
    
    if ! "$PG_READY_BIN" -h localhost -p 5432 >/dev/null 2>&1 && ! nc -z localhost 5432 >/dev/null 2>&1; then
        DB_VERIFY_OK=0
        DB_STATUS_MSG="PostgreSQL port 5432 not responding"
    else
        # 3.2 harness_dev DB 접속 검사
        if ! psql -h localhost -U harness -d harness_dev -c "SELECT 1" >/dev/null 2>&1; then
            # psql이 없는 경우 가상환경 python으로 직접 시도
            PROJECT_ROOT="/Users/juntaepark/projects/harness-platform"
            if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
                if ! "${PROJECT_ROOT}/.venv/bin/python" -c "import psycopg2; psycopg2.connect('postgresql://localhost/harness_dev')" >/dev/null 2>&1; then
                    DB_VERIFY_OK=0
                    DB_STATUS_MSG="harness_dev connection failed via psycopg2"
                fi
            else
                DB_VERIFY_OK=0
                DB_STATUS_MSG="harness_dev connection failed via psql"
            fi
        fi
    fi

    # DB 장애 발생 시 자동 복구 개입
    if [[ "$DB_VERIFY_OK" -eq 0 ]]; then
        log "DATABASE ERROR: ${DB_STATUS_MSG} -> Attempting self-healing..."
        
        # 1. Homebrew postgresql 재시동
        if brew services restart postgresql@16 >/dev/null 2>&1 || brew services restart postgresql >/dev/null 2>&1; then
            log "Homebrew PostgreSQL restarted successfully."
            sleep 4
        else
            log "Failed to restart Homebrew postgresql. Attempting launchctl kickstart..."
            launchctl kickstart -k "gui/$(id -u)/homebrew.mxcl.postgresql@16" >/dev/null 2>&1 || true
            sleep 4
        fi

        # 2. OpenClaw Bridge & Gateway 동시 재시동하여 연결 세션 리빌딩
        log "Rebooting OpenClaw components to establish fresh database pool..."
        launchctl kickstart -k "gui/$(id -u)/com.harness.openclaw-bridge" >/dev/null 2>&1 || true
        launchctl kickstart -k "gui/$(id -u)/ai.openclaw.gateway" >/dev/null 2>&1 || true
    fi

    log "OK pid=${PID} gateway=reachable(${HTTP_CODE}) db=${DB_STATUS_MSG}"
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
