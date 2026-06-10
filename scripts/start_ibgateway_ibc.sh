#!/bin/bash
# IB Gateway 자동 시작 — IBC 무인 로그인(-inline, Terminal 우회) → 실패 시 open 폴백.
#
# 근본 원인 메모(2026-06-10 규명):
#  1) IBC의 gatewaystartmacos.sh는 osascript로 Terminal을 조종해 로그인하는데, 비대화형
#     컨텍스트에서 AppleEvent 타임아웃(-1712). → `-inline` 인자로 Terminal 우회(직접 exec).
#  2) IB Gateway는 GUI(Aqua) 세션이 필수다(java.awt.HeadlessException). 이 스크립트는
#     launchd LaunchAgent(domain=gui/<uid>)가 실행하므로 이미 GUI 세션에 attach돼 있다.
#     (SSH로 직접 실행하면 GUI 세션 밖이라 HeadlessException 발생 — 운영 경로 아님.)
#  3) GUI 세션 자체가 없으면(재부팅 후 자동 로그인 OFF 등) 어떤 방법으로도 구동 불가 → 명시 경고.

PROJ="/Users/juntaepark/projects/harness-platform"
LOG="$PROJ/docs/reports/ibgateway_ibc.log"
# IBC 런처의 raw stdout/stderr 전용(설정 파싱 진단·계정ID 등 민감정보 분리). runtime/은 .gitignore 대상.
IBC_RAW_LOG="$PROJ/runtime/ibgateway_ibc_raw.log"
ENV_FILE="$PROJ/.env"
GW_APP="/Users/juntaepark/Applications/IB Gateway 10.45/IB Gateway 10.45-1.app"
STATUS_HELPER="$PROJ/scripts/ibkr_gateway_runtime_status.py"
IBC_LAUNCHER="$HOME/IBC/gatewaystartmacos.sh"
IBC_WAIT_SEC=90        # IBC 무인 로그인 대기
FALLBACK_WAIT_SEC=60   # open 폴백 후 대기(수동 로그인 여지)
POLL_INTERVAL_SEC=5

mkdir -p "$(dirname "$LOG")"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
write_status() {
    if [ -x "$PROJ/.venv/bin/python" ] && [ -f "$STATUS_HELPER" ]; then
        "$PROJ/.venv/bin/python" "$STATUS_HELPER" \
            --status "$1" \
            --message "$2" \
            --source "start_ibgateway_ibc" \
            --wait-timeout-sec "$IBC_WAIT_SEC" \
            > /dev/null 2>&1 || true
    fi
}
gw_up() { lsof -i :4002 2>/dev/null | grep -q LISTEN; }
wait_for_gw() {  # $1=대기 초
    local total="$1" waited=0
    while [ "$waited" -lt "$total" ]; do
        sleep "$POLL_INTERVAL_SEC"
        waited=$((waited + POLL_INTERVAL_SEC))
        gw_up && return 0
    done
    return 1
}
slack() { [ -n "${SLACK_WEBHOOK_URL:-}" ] && curl -s -X POST "$SLACK_WEBHOOK_URL" -H 'Content-Type: application/json' -d "$1" > /dev/null 2>&1; }

# 이미 실행 중이면 종료
if gw_up; then
    log "IB Gateway 이미 실행 중 (port 4002) — 스킵"
    write_status "ready" "IB Gateway가 이미 실행 중이며 API 포트 4002가 열려 있습니다."
    exit 0
fi

# .env 로드 (Slack 알림용)
if [ -f "$ENV_FILE" ]; then
    set -a; source "$ENV_FILE"; set +a
fi

# GUI(Aqua) 세션 존재 확인 — 없으면 게이트웨이 구동 자체가 불가(HeadlessException)
CONSOLE_USER=$(stat -f "%Su" /dev/console 2>/dev/null)
if [ "$CONSOLE_USER" != "juntaepark" ]; then
    log "[ERROR] 콘솔 GUI 세션에 juntaepark 없음(현재: '$CONSOLE_USER') — Aqua 세션 부재. 게이트웨이 구동 불가."
    write_status "offline" "Mac Mini에 juntaepark GUI 로그인이 없어 IB Gateway를 띄울 수 없습니다(재부팅 후 자동 로그인 OFF 등). 화면공유로 GUI 로그인이 필요합니다."
    slack '{"text":"🚨 *[IB Gateway]* Aqua GUI 세션 없음 — Mac Mini 화면 GUI 로그인 필요(이 상태에선 자동매매 불가)"}'
    exit 1
fi

# 1순위: IBC 무인 로그인(-inline, Terminal 우회). LaunchAgent(gui 세션)가 실행하므로 GUI 접근 가능.
if [ -f "$IBC_LAUNCHER" ]; then
    log "=== IB Gateway 시작 (IBC 무인 로그인, -inline) ==="
    write_status "launching" "IBC 무인 로그인 시작 — 저장된 자격증명으로 자동 로그인 중(수동 입력 불필요)."
    mkdir -p "$(dirname "$IBC_RAW_LOG")"
    # -inline: displaybannerandlaunch.sh를 직접 exec(osascript/Terminal 우회).
    # IBC를 *새 세션(setsid)*으로 완전 분리한다. 이유: launchd 잡이 main 스크립트 종료 시
    # 잡 프로세스그룹을 함께 reap하므로, `nohup &`만으론 IBC/게이트웨이가 같이 죽는다
    # (2026-06-10 실측: 부팅 잡 직접 실행 시 reap됨). macOS엔 setsid 바이너리가 없어 python의
    # start_new_session=True(os.setsid)로 분리 → 부팅 잡·watchdog 양쪽 모두 게이트웨이 생존.
    PYBIN="$PROJ/.venv/bin/python"; [ -x "$PYBIN" ] || PYBIN="/usr/bin/python3"
    "$PYBIN" -c "import subprocess,sys; subprocess.Popen(['/bin/bash', sys.argv[1], '-inline'], stdout=open(sys.argv[2],'a'), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)" "$IBC_LAUNCHER" "$IBC_RAW_LOG"
    log "IBC -inline 분리 실행(새 세션, setsid) — 최대 ${IBC_WAIT_SEC}s 대기"
    if wait_for_gw "$IBC_WAIT_SEC"; then
        log "✅ IBC 무인 로그인 성공 — port 4002 OPEN (대표 수동 로그인 불필요)"
        write_status "ready" "IBC 무인 로그인 완료. 다음 스캔부터 즉시 사용 가능(수동 로그인 없이 자동 복구)."
        exit 0
    fi
    log "[WARN] IBC ${IBC_WAIT_SEC}s 내 미연결 → open 폴백으로 전환"
fi

# 2순위: open 폴백 — 게이트웨이 앱을 GUI 세션에서 정식 실행(수동 로그인 필요할 수 있음)
if [ -d "$GW_APP" ]; then
    log "=== [폴백] open 방식 ==="
    write_status "launching" "open 폴백 — 로그인 창에서 수동 로그인/2FA가 필요할 수 있습니다."
    open "$GW_APP"
    if wait_for_gw "$FALLBACK_WAIT_SEC"; then
        log "✅ open 폴백 연결 성공 — port 4002 OPEN"
        write_status "ready" "IB Gateway 연결이 완료되었습니다."
        exit 0
    fi
    log "[WARN] open 폴백도 ${FALLBACK_WAIT_SEC}s 내 미연결 — 수동 2FA 대기로 간주"
    write_status "waiting_for_2fa" "IB Gateway는 실행됐지만 로그인이 끝나지 않았습니다. Mac Mini 로그인 창과 IBKR Mobile 승인을 확인하세요."
    slack '{"text":"ℹ *[IB Gateway]* 무인 로그인 실패 → 수동 로그인 필요\n• Mac Mini 화면 로그인 창 확인\n• 비밀번호 입력 후 IBKR Mobile 2FA 승인\n• 승인 완료 후 다음 스캔이 자동 진행됩니다"}'
    exit 1
fi

log "[ERROR] IBC 런처($IBC_LAUNCHER)·게이트웨이 앱($GW_APP) 모두 없음"
write_status "offline" "IBC 런처와 IB Gateway 앱을 모두 찾지 못했습니다."
exit 1
