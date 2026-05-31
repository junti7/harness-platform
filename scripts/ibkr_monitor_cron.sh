#!/bin/bash
# IBKR Turtle Monitor — 장중 자동 신호 스캔 + Slack 알림
# crontab 등록:
#   KRX  (09:00-15:30 KST = 00:00-06:30 UTC): */30 0-6 * * 1-5
#   NYSE (09:30-16:00 EST = 14:30-21:00 UTC): */30 14-20 * * 1-5

PROJ="/Users/juntaepark/projects/harness-platform"
LOG="$PROJ/docs/reports/ibkr_monitor_cron.log"
IBC_SCRIPT="$PROJ/scripts/start_ibgateway_ibc.sh"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

cd "$PROJ" || exit 1

# ── IB Gateway 상태 확인 + 자동 시작 ────────────────────────────────────────
if ! lsof -i :4002 2>/dev/null | grep -q LISTEN; then
    log "[GATEWAY] 오프라인 — IBC 자동 시작 시도"

    # IBC 시작 (백그라운드)
    bash "$IBC_SCRIPT" &
    IBC_PID=$!

    # 최대 90초 대기
    WAITED=0
    while [ $WAITED -lt 90 ]; do
        sleep 5; WAITED=$((WAITED+5))
        if lsof -i :4002 2>/dev/null | grep -q LISTEN; then
            log "[GATEWAY] ✅ ${WAITED}초 후 연결 성공"
            break
        fi
    done

    if ! lsof -i :4002 2>/dev/null | grep -q LISTEN; then
        log "[GATEWAY] ❌ 90초 내 연결 실패 — 2FA 대기 중이거나 로그인 오류. 스캔 건너뜀."

        # Slack 알림: 수동 2FA 승인 요청
        WEBHOOK=$(grep SLACK_WEBHOOK_URL "$PROJ/.env" 2>/dev/null | cut -d= -f2-)
        if [ -n "$WEBHOOK" ]; then
            curl -s -X POST "$WEBHOOK" \
                -H 'Content-Type: application/json' \
                -d '{"text":"⚠ *[IB Gateway]* 자동 시작 실패\n• IBKR Mobile 앱에서 2FA 승인이 필요합니다\n• 승인 후 다음 cron 실행(30분 이내)에 자동 재시도됩니다"}' \
                > /dev/null 2>&1
        fi
        exit 0
    fi
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
