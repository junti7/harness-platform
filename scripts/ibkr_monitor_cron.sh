#!/bin/bash
# IBKR Turtle Monitor — 장중 자동 신호 스캔 + Slack 알림
# crontab 등록:
#   KRX  (09:00-15:30 KST = 00:00-06:30 UTC): */30 0-6 * * 1-5
#   NYSE (09:30-16:00 EST = 14:30-21:00 UTC): */30 14-20 * * 1-5

PROJ="/Users/juntaepark/projects/harness-platform"
LOG="$PROJ/docs/reports/ibkr_monitor_cron.log"
IBC_SCRIPT="$PROJ/scripts/start_ibgateway_ibc.sh"
STATUS_HELPER="$PROJ/scripts/ibkr_gateway_runtime_status.py"
WAIT_TIMEOUT_SEC=120
POLL_INTERVAL_SEC=5

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }
write_status() {
    if [ -x "$PROJ/.venv/bin/python" ] && [ -f "$STATUS_HELPER" ]; then
        "$PROJ/.venv/bin/python" "$STATUS_HELPER" \
            --status "$1" \
            --message "$2" \
            --source "ibkr_monitor_cron" \
            --wait-timeout-sec "$WAIT_TIMEOUT_SEC" \
            > /dev/null 2>&1 || true
    fi
}

cd "$PROJ" || exit 1

# ── IB Gateway 상태 확인 + 자동 시작 ────────────────────────────────────────
if ! lsof -i :4002 2>/dev/null | grep -q LISTEN; then
    log "[GATEWAY] 오프라인 — IBC 자동 시작 시도"
    write_status "launching" "장중 스캔 전에 IB Gateway 자동 시작을 시도하는 중입니다."

    # IBC 시작 (백그라운드)
    bash "$IBC_SCRIPT" &
    IBC_PID=$!

    # 최대 120초 대기
    WAITED=0
    while [ $WAITED -lt "$WAIT_TIMEOUT_SEC" ]; do
        sleep "$POLL_INTERVAL_SEC"; WAITED=$((WAITED + POLL_INTERVAL_SEC))
        if lsof -i :4002 2>/dev/null | grep -q LISTEN; then
            log "[GATEWAY] ✅ ${WAITED}초 후 연결 성공"
            write_status "ready" "IB Gateway 연결이 완료되어 신호 스캔을 계속 진행합니다."
            break
        fi
    done

    if ! lsof -i :4002 2>/dev/null | grep -q LISTEN; then
        log "[GATEWAY] ⚠ ${WAIT_TIMEOUT_SEC}초 내 포트 오픈 확인 실패 — 2FA 승인 대기 상태로 간주. 이번 스캔 건너뜀."
        write_status "waiting_for_2fa" "IB Gateway는 실행됐지만 2FA 승인 전입니다. 이번 스캔은 건너뛰고 다음 주기에 자동 재시도합니다."

        # Slack 알림: 수동 2FA 승인 요청
        WEBHOOK=$(grep SLACK_WEBHOOK_URL "$PROJ/.env" 2>/dev/null | cut -d= -f2-)
        if [ -n "$WEBHOOK" ]; then
            curl -s -X POST "$WEBHOOK" \
                -H 'Content-Type: application/json' \
                -d '{"text":"ℹ *[IB Gateway]* 2FA 승인 대기 중\n• IBKR Mobile 앱에서 2FA 승인이 필요합니다\n• 승인 후 다음 cron 실행 시 자동 재시도됩니다"}' \
                > /dev/null 2>&1
        fi
        exit 0
    fi
else
    write_status "ready" "IB Gateway가 이미 연결되어 있어 바로 신호 스캔을 진행합니다."
fi

# ── 신호 스캔 ────────────────────────────────────────────────────────────────
log "[CRON] 신호 스캔 시작"
source .venv/bin/activate

python scripts/ibkr_turtle_monitor.py --json \
    > /tmp/ibkr_monitor_out.json 2>> "$LOG"

if [ $? -eq 0 ]; then
    SIGNALS=$(python3 -c "
import json
d = json.load(open('/tmp/ibkr_monitor_out.json'))
bs = [c['symbol'] for c in d.get('entry_candidates', []) if c.get('signal') == 'breakout_long' and not c.get('in_position')]
exits = d.get('exit_signals', [])
print(f'breakout={len(bs)} exit={len(exits)}')
" 2>/dev/null)
    log "[CRON] 완료: $SIGNALS"
else
    log "[CRON] 오류 발생"
fi
