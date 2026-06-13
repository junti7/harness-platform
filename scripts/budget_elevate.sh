#!/bin/bash
# 예산 임시 상향(elevation) — 명시적·승인·TTL 부여. [AR-053] (macOS/Mac Mini 전용)
# 이 스크립트로만 한도를 올린다(ad-hoc `sed -i .env` 금지). 마커를 남겨
# budget_revert_check.sh가 TTL/throughput/백로그로 자동 원복하게 한다.
#
# 사용: scripts/budget_elevate.sh <limit_usd> <hours> "<reason>" "<approved_by>"
#   예: scripts/budget_elevate.sh 100000 24 "edu 백로그 23k 드레인" "대표 2026-06-13"
#
# DAILY_COST_LIMIT_USD는 유료 LLM 지출 envelope를 가두는 가드레일(ceiling)이다. 이를 올리는 것은
# 실제 지출 한도를 넓히는 의도적 결정이므로 **승인자(approved_by) 기재를 강제**하고, 금액/TTL 상한과
# 마커 로깅으로 봉쇄한다. (capital_action_approve와의 경계는 거버넌스 결정 사항으로 CEO에 보고됨.)
set -uo pipefail
cd "$HOME/projects/harness-platform" || exit 1
ENVF=".env"   # 프로덕션은 항상 프로젝트 .env (외부 ENVF 주입 무시; 테스트는 lib 직접 source)
source scripts/_budget_lib.sh
LIMIT="${1:?사용: budget_elevate.sh <limit_usd> <hours> \"<reason>\" \"<approved_by>\"}"
HOURS="${2:?hours(상향 유지 시간) 필요}"
REASON="${3:?reason(상향 사유) 필요}"
APPROVED_BY="${4:?approved_by(승인자: 이름+날짜) 필요 — 무승인 상향 금지}"
MAXH="${BUDGET_ELEVATION_MAX_HOURS:-48}"     # TTL 상한(시간)
CAP="${BUDGET_ELEVATION_MAX_USD:-100000}"    # 금액 상한(이 이상 상향 거부)
# 상한 config 자체가 비정상(음수/비숫자)이면 안전 기본값으로 폴백(모순 상태 방지)
is_pos_num "$CAP"  || { echo "[budget-elevate] BUDGET_ELEVATION_MAX_USD='$CAP' 비정상 → 100000" >&2; CAP=100000; }
is_pos_num "$MAXH" || { echo "[budget-elevate] BUDGET_ELEVATION_MAX_HOURS='$MAXH' 비정상 → 48" >&2; MAXH=48; }

# --- 승인자 검증: 공백/빈값 거부(감사 추적용 식별자 강제) ---
case "$(printf '%s' "$APPROVED_BY" | tr -d '[:space:]')" in
  "") echo "[budget-elevate] 거부: approved_by 가 비어 있다(이름+날짜 기재)."; exit 1 ;;
esac

# --- 입력 검증: 숫자/양수/상한 (값은 argv 전달 — 코드 인젝션 차단) ---
is_pos_num "$LIMIT" || { echo "[budget-elevate] 거부: limit '$LIMIT' 가 양수 숫자가 아니다."; exit 1; }
is_pos_num "$HOURS" || { echo "[budget-elevate] 거부: hours '$HOURS' 가 양수 숫자가 아니다."; exit 1; }
num_le "$LIMIT" "$CAP" || { echo "[budget-elevate] 거부: limit=$LIMIT > 금액 상한 ${CAP}."; exit 1; }
num_le "$HOURS" "$MAXH" || { echo "[budget-elevate] 거부: hours=$HOURS > TTL 상한 ${MAXH}h(반복 상향은 재실행)."; exit 1; }

# --- .env 동시 수정 방지(PID 생존검사 + stale 회수; 최대 ~10초 대기) ---
if ! budget_acquire_lock 20; then echo "[budget-elevate] 거부: 락 획득 실패(다른 예산 작업 진행 중)."; exit 1; fi
trap 'budget_release_lock' EXIT

# 마커를 .env 변경보다 먼저 기록(부분실패 시에도 '상향됐는데 마커없음' 창을 만들지 않음).
python3 - "$LIMIT" "$HOURS" "$REASON" "$APPROVED_BY" <<'PY'
import sys, json, time
json.dump(
    {"created_epoch": int(time.time()), "limit": sys.argv[1], "hours": float(sys.argv[2]),
     "reason": sys.argv[3], "approved_by": sys.argv[4]},
    open("runtime/budget_elevation.json", "w"), ensure_ascii=False, indent=2)
PY
if ! set_env_var DAILY_COST_LIMIT_USD "$LIMIT"; then
  echo "[budget-elevate] !! .env 반영/검증 실패 — 마커 제거하고 중단(부분상태 방지)"
  rm -f runtime/budget_elevation.json; exit 1
fi
echo "[budget-elevate] 한도=$LIMIT/day, TTL=${HOURS}h, 승인=$APPROVED_BY, 사유: $REASON"
echo "[budget-elevate] $(grep '^DAILY_COST_LIMIT_USD=' "$ENVF") / 마커: runtime/budget_elevation.json"
echo "[budget-elevate] 자동 원복: budget_revert_check(매일 10:30 KST)가 TTL 만료/throughput 0/백로그 소진 중 먼저 오는 것에 원복."

# 감사 추적용 Slack 기록(best-effort)
python3 - "$LIMIT" "$HOURS" "$REASON" "$APPROVED_BY" <<'PY' 2>/dev/null || true
import sys
from adapters.content.slack_router import send_slack_route
send_slack_route("ops_incidents", {"text":
  f":arrow_up: [예산 상향] 한도 ${sys.argv[1]}/day, TTL {sys.argv[2]}h — 승인: {sys.argv[4]} / 사유: {sys.argv[3]}. "
  f"자동 원복(budget_revert_check)이 TTL/throughput/백로그로 관리."})
PY
