#!/bin/bash
# IBKR Turtle Monitor — 장중 자동 신호 스캔 + Slack 알림
# crontab 등록:
#   KRX  (09:00-15:30 KST = 00:00-06:30 UTC): */30 0-6 * * 1-5
#   NYSE (09:30-16:00 EST = 14:30-21:00 UTC): */30 14-20 * * 1-5

PROJ="/Users/juntaepark/projects/harness-platform"
LOG="$PROJ/docs/reports/ibkr_monitor_cron.log"

cd "$PROJ" || exit 1
source .venv/bin/activate

echo "$(date '+%Y-%m-%d %H:%M:%S') [CRON] 신호 스캔 시작" >> "$LOG"

python scripts/ibkr_turtle_monitor.py --json \
    > /tmp/ibkr_monitor_out.json 2>> "$LOG"

if [ $? -eq 0 ]; then
    SIGNALS=$(python3 -c "
import json, sys
d = json.load(open('/tmp/ibkr_monitor_out.json'))
bs = [c['symbol'] for c in d.get('entry_candidates', []) if c.get('signal') == 'breakout_long' and not c.get('in_position')]
exits = d.get('exit_signals', [])
print(f'breakout={len(bs)} exit={len(exits)}')
" 2>/dev/null)
    echo "$(date '+%Y-%m-%d %H:%M:%S') [CRON] 완료: $SIGNALS" >> "$LOG"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') [CRON] 오류 발생" >> "$LOG"
fi
