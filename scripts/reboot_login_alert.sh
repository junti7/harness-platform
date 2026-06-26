#!/bin/bash
# 재부팅 후 로그인 Slack 알림 — gui LaunchAgent(RunAtLoad)로 *GUI 로그인 시점*에 실행된다.
#
# 목적: 재부팅이 일어나 CEO가 FileVault 잠금해제 + GUI 로그인을 마치면, 그 사실과
#       IB Gateway 자동 기동 성공/실패를 Slack으로 알린다.
#
# ── FileVault 한계(중요) ────────────────────────────────────────────────
#   재부팅 직후 멈추는 *FileVault 잠금해제 화면*에서는 디스크가 암호화돼 있어 OS도
#   네트워크도 없다. 즉 "잠금해제가 필요한 바로 그 순간"에는 Mac Mini가 스스로 Slack을
#   보낼 수 없다. 이 잡은 *잠금해제 + 로그인 이후* 시점부터 동작한다. CEO가 자리에 없는
#   상태(부팅 화면 방치)를 커버하려면 별도의 외부 heartbeat 감시자가 필요하다.
# ────────────────────────────────────────────────────────────────────────
#
# 스팸 방지: launchd가 이 agent를 (재)load 할 때마다 RunAtLoad가 켜지므로, 부팅 후
#   경과시간(uptime)이 짧을 때 = 실제 재부팅 직후 로그인일 때만 알림을 보낸다.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJ/.env"
LOG="$PROJ/logs/reboot-login-alert.log"
FRESH_BOOT_SEC=900   # 부팅 후 이 시간(초) 이내 로그인만 "재부팅 직후"로 간주
GW_WAIT_SEC=480      # IB Gateway 자동 기동 추적 최대 대기

mkdir -p "$(dirname "$LOG")"
log() { echo "$(date '+%F %T') $*" >>"$LOG"; }

# .env 로드 (SLACK_WEBHOOK_URL). 시크릿은 로그/출력에 노출하지 않는다.
[ -f "$ENV_FILE" ] && { set -a; source "$ENV_FILE"; set +a; }

HOST="$(scutil --get ComputerName 2>/dev/null || hostname -s)"
slack() { [ -n "${SLACK_WEBHOOK_URL:-}" ] && curl -s -m 10 -X POST "$SLACK_WEBHOOK_URL" -H 'Content-Type: application/json' -d "$1" >/dev/null 2>&1; }
gw_up() { nc -z -G 2 127.0.0.1 4002 >/dev/null 2>&1; }

# 부팅 후 경과초
boot_sec="$(sysctl -n kern.boottime 2>/dev/null | sed -n 's/.*sec = \([0-9]\{6,\}\).*/\1/p')"
now="$(date +%s)"
up=$(( now - ${boot_sec:-0} ))
log "start uptime=${up}s gw_up=$(gw_up && echo yes || echo no)"

if [ -z "$boot_sec" ] || [ "$up" -gt "$FRESH_BOOT_SEC" ]; then
    log "uptime ${up}s > ${FRESH_BOOT_SEC}s(또는 미상) — 재부팅 직후 아님. 알림 스킵."
    exit 0
fi

# 부팅 직후 네트워크(DNS/route) 준비 대기
for _ in $(seq 1 20); do curl -s -m 3 -o /dev/null https://slack.com && break; sleep 2; done

slack "{\"text\":\"♻️ *[$HOST]* 재부팅 후 로그인 감지 — FileVault 잠금해제·GUI 로그인 완료. IB Gateway 자동 기동 확인 중...\"}"
log "sent reboot banner"

# IB Gateway(4002) 자동 기동 추적
deadline=$(( now + GW_WAIT_SEC ))
while [ "$(date +%s)" -lt "$deadline" ]; do
    if gw_up; then
        slack "{\"text\":\"✅ *[$HOST]* IB Gateway 자동 기동 완료 (port 4002 OPEN) — IBKR 거래 가능. 추가 조치 불필요.\"}"
        log "gateway up — done"
        exit 0
    fi
    sleep 15
done

slack "{\"text\":\"🚨 *[$HOST]* 재부팅 후 ${GW_WAIT_SEC}s 내 IB Gateway 미기동 (port 4002 CLOSED) — 게이트웨이/IBC 로그인 상태 확인 필요.\"}"
log "gateway DOWN after ${GW_WAIT_SEC}s"
exit 0
