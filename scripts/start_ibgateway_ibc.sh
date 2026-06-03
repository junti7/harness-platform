#!/bin/bash
# IB Gateway 자동 시작 — macOS open 명령 사용
# IBC(IbcAlpha)는 HeadlessException으로 headless 환경에서 작동하지 않음
# macOS open은 GUI 세션에서 앱을 정식으로 실행하므로 안정적

PROJ="/Users/juntaepark/projects/harness-platform"
LOG="$PROJ/docs/reports/ibgateway_ibc.log"
ENV_FILE="$PROJ/.env"
GW_APP="/Users/juntaepark/Applications/IB Gateway 10.45/IB Gateway 10.45-1.app"
STATUS_HELPER="$PROJ/scripts/ibkr_gateway_runtime_status.py"
WAIT_TIMEOUT_SEC=120
POLL_INTERVAL_SEC=5

mkdir -p "$(dirname "$LOG")"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
write_status() {
    if [ -x "$PROJ/.venv/bin/python" ] && [ -f "$STATUS_HELPER" ]; then
        "$PROJ/.venv/bin/python" "$STATUS_HELPER" \
            --status "$1" \
            --message "$2" \
            --source "start_ibgateway_ibc" \
            --wait-timeout-sec "$WAIT_TIMEOUT_SEC" \
            > /dev/null 2>&1 || true
    fi
}

# 이미 실행 중이면 종료
if lsof -i :4002 2>/dev/null | grep -q LISTEN; then
    log "IB Gateway 이미 실행 중 (port 4002) — 스킵"
    write_status "ready" "IB Gateway가 이미 실행 중이며 API 포트 4002가 열려 있습니다."
    exit 0
fi

log "=== IB Gateway 시작 (open 방식) ==="
write_status "launching" "IB Gateway를 실행했습니다. 로그인 창과 앱 구동을 확인하는 중입니다."

if [ ! -d "$GW_APP" ]; then
    log "[ERROR] IB Gateway 앱 없음: $GW_APP"
    write_status "offline" "IB Gateway 앱을 찾지 못했습니다."
    exit 1
fi

# macOS open으로 GUI 앱 실행 (GUI 세션 필요)
open "$GW_APP"
log "IB Gateway 앱 열기 요청 완료 — 로그인 창에서 비밀번호 입력 후 IBKR Mobile에서 2FA 승인해주세요"

# .env 로드 (Slack 알림용)
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
fi

# 포트 4002 열릴 때까지 대기 (최대 120초)
for i in $(seq 1 $((WAIT_TIMEOUT_SEC / POLL_INTERVAL_SEC))); do
    sleep "$POLL_INTERVAL_SEC"
    if lsof -i :4002 2>/dev/null | grep -q LISTEN; then
        log "✅ IB Gateway 연결 성공 (${i}×${POLL_INTERVAL_SEC}초)"
        write_status "ready" "IB Gateway 연결이 완료되었습니다. 다음 스캔부터 즉시 사용 가능합니다."
        exit 0
    fi
done

# 타임아웃 → Slack 알림
log "[WARN] ${WAIT_TIMEOUT_SEC}초 내 포트 오픈 확인 실패 — 2FA 승인 대기 상태로 간주"
write_status "waiting_for_2fa" "IB Gateway는 실행됐지만 아직 2FA 승인이 끝나지 않았습니다. Mac Mini 로그인 창과 IBKR Mobile 승인을 확인하세요."
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    curl -s -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d '{"text":"ℹ *[IB Gateway]* 2FA 승인 대기 중\n• Mac Mini 화면에서 로그인 창 확인\n• 비밀번호 입력 후 IBKR Mobile 2FA 승인\n• 승인 완료 후 다음 스캔이 자동 진행됩니다"}' \
        > /dev/null 2>&1
fi
exit 1
