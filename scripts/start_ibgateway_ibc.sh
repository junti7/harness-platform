#!/bin/bash
# IB Gateway 자동 시작 (IBC 사용)
# .env에서 IBKR_PAPER_PASSWORD를 읽어 IBC에 주입
# 2FA: IBKR Mobile 앱에서 1회 승인 필요

PROJ="/Users/juntaepark/projects/harness-platform"
LOG="$PROJ/docs/reports/ibgateway_ibc.log"
ENV_FILE="$PROJ/.env"
IBC_PATH="/Users/juntaepark/IBC"
TWS_PATH="/Users/juntaepark/Applications"

mkdir -p "$(dirname "$LOG")"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }

# 이미 실행 중이면 종료
if lsof -i :4002 2>/dev/null | grep -q LISTEN; then
    log "IB Gateway 이미 실행 중 (port 4002) — 스킵"
    exit 0
fi

IBC_VER=$(cat "$IBC_PATH/version" 2>/dev/null || echo "?")
log "=== IB Gateway 시작 (IBC v$IBC_VER) ==="

# .env 로드
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

if [ -z "$IBKR_PAPER_PASSWORD" ]; then
    log "[ERROR] IBKR_PAPER_PASSWORD 미설정 — $ENV_FILE 확인 필요"
    exit 1
fi

mkdir -p "$IBC_PATH/logs"
log "IBC 시작 — IBKR Mobile 앱에서 2FA 승인해주세요"

# ibcstart.sh 인자 방식 호출 (백그라운드)
nohup "$IBC_PATH/scripts/ibcstart.sh" 10.45 \
    --gateway \
    --tws-path="$TWS_PATH" \
    --ibc-path="$IBC_PATH" \
    --ibc-ini="$IBC_PATH/config.ini" \
    --user=vvgfmt298 \
    --pw="$IBKR_PAPER_PASSWORD" \
    --mode=paper \
    --on2fatimeout=restart \
    >> "$LOG" 2>&1 &

log "IBC PID: $! — IBKR Mobile에서 2FA 승인 후 자동 연결됩니다"
