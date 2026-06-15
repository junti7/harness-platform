#!/bin/bash
# 임시 예산 상향(elevation)의 시간/처리량 기반 자동 원복 점검 (멱등). [AR-053]
# (macOS/Mac Mini 전용 launchd 잡. 매일 10:30 KST.)
#
# 평상시 기본값은 **유한 한도($DEFAULT)** 다. 무제한은 resting state가 될 수 없다.
# 예산 상향은 아래 조건이 모두 살아있을 때만 유지된다:
#   (1) 명시적 elevation 마커(runtime/budget_elevation.json) 존재 — scripts/budget_elevate.sh로만 생성
#   (2) TTL 이내 (시간 조건)               (3) 최근 창 정제 산출 > 0 (throughput, outage 감지)
#   (4) 백로그가 아직 남아있음 (드레인 미완)
# 하나라도 깨지면 즉시 유한 기본값으로 복귀. 단일 백로그 의존을 제거했다.
#
# 과거 결함(고친 것): 원복 조건이 "백로그 소진" 단일 조건뿐이라, provider outage로 throughput=0이
#   되면 백로그가 늘어 조건이 영구 미충족 → 무제한이 며칠씩 고착됐다. (memory project_temp_unlimited_budget.md)
set -uo pipefail
cd "$HOME/projects/harness-platform" || exit 1
export PATH="/opt/homebrew/bin:$PATH"
source .venv/bin/activate 2>/dev/null
ENVF=".env"   # 프로덕션은 항상 프로젝트 .env (외부 ENVF 주입 무시; 테스트는 lib 직접 source)
source scripts/_budget_lib.sh

DEFAULT="${DAILY_COST_LIMIT_DEFAULT:-2.00}"   # 평상시 유한 기본값(이상 가드레일). 실지출 $0~1/일이라 $2면 정상운영 무영향+폭주 조기차단(CEO 2026-06-16, 기존 30.00에서 하향).
QUOTA_PENDING="runtime/gemini_quota_revert_pending.flag"   # 쿼터 원복 실패 시 재시도 신호(fail-closed)
MAX_HOURS="${BUDGET_ELEVATION_MAX_HOURS:-48}"    # elevation 절대 TTL 상한(시간)
RECENT_HOURS="${BUDGET_THROUGHPUT_WINDOW_H:-6}"  # throughput 판정 창(시간)
MARKER="runtime/budget_elevation.json"

slack() { # $1=text
  python3 - "$1" <<'PY' 2>/dev/null || true
import sys
from adapters.content.slack_router import send_slack_route
send_slack_route("ops_incidents", {"text": sys.argv[1]})
PY
}

# --- .env 동시 수정 방지(PID 생존검사 + stale 자동 회수). 잡히면 살아있는 다른 인스턴스가 처리. ---
if ! budget_acquire_lock 1; then
  echo "[budget-revert-check] 다른 예산 작업 진행 중(락) — skip"; exit 0
fi
trap 'budget_release_lock' EXIT

# --- 아침 정상화: QA LLM 재활성. QA는 회사 필수(qa_clear)이므로 hold-off 플래그가 없으면
#     현재 값이 true가 아닐 때(=false 이거나 키 부재) 항상 true로 보장한다(부재 케이스도 복원). ---
if [ -f runtime/qa_llm_hold_off.flag ]; then
  echo "[budget-revert-check] QA_LLM hold-off 플래그 감지 — 자동 복원 건너뜀"
elif [ "$(grep -E '^QA_LLM_ENABLED=' "$ENVF" | cut -d= -f2)" != "true" ]; then
  if set_env_var QA_LLM_ENABLED true; then
    echo "[budget-revert-check] QA_LLM_ENABLED=true 복원"
    slack ":information_source: [budget-revert-check] QA_LLM_ENABLED 자동 복원(true). 의도적 비활성이면 runtime/qa_llm_hold_off.flag 생성."
  else slack ":warning: [budget-revert-check] QA_LLM_ENABLED 복원 실패(.env 확인)"; fi
fi

CUR=$(grep -E '^DAILY_COST_LIMIT_USD=' "$ENVF" | cut -d= -f2); CUR="${CUR:-}"

# gemini per-day 쿼터를 평상치(3000)로 복귀(best-effort, 멱등). 실패 시 1 리턴.
revert_gemini_quota() {
  local GP="generativelanguage.googleapis.com" PROJ="projects/gen-lang-client-0280653202" UNIT="1/d/{project}/{model}" qok=0
  gcloud alpha services quota update --service=$GP --consumer=$PROJ --metric=$GP/generate_content_paid_tier_2_requests --unit="$UNIT" --value=3000 --force >/dev/null 2>&1 || qok=1
  gcloud alpha services quota update --service=$GP --consumer=$PROJ --metric=$GP/generate_content_paid_tier_3_requests --unit="$UNIT" --value=3000 --force >/dev/null 2>&1 || qok=1
  return $qok
}

# fail-closed 재시도: 지난 원복에서 쿼터 복귀가 실패해 pending 플래그가 남았으면 매 실행에서 재시도.
if [ -f "$QUOTA_PENDING" ]; then
  if revert_gemini_quota; then rm -f "$QUOTA_PENDING"; echo "[budget-revert-check] 지연된 gemini 쿼터 복귀 재시도 성공 — pending 해제"
  else echo "[budget-revert-check] gemini 쿼터 복귀 여전히 실패 — pending 유지(다음 실행 재시도)"; fi
fi

# 원복: .env 반영을 검증한 뒤에만 마커 삭제. 마커가 있었으면(=elevation 정리) CUR==DEFAULT라도 쿼터까지 수렴.
revert_to_default() { # $1=사유
  local reason="$1" had_marker=0 qmsg=""
  [ -f "$MARKER" ] && had_marker=1
  if [ "$CUR" != "$DEFAULT" ]; then
    if ! set_env_var DAILY_COST_LIMIT_USD "$DEFAULT"; then
      echo "[budget-revert-check] !! 원복 실패: .env 반영/검증 실패 — 마커 보존, 경보"
      slack ":rotating_light: [예산 원복 실패] $reason 인데 .env 쓰기/검증 실패. 수동 확인 필요(마커 보존)."
      return 1
    fi
    echo "[budget-revert-check] 원복: 한도 ${CUR:-(없음)} → $DEFAULT ($reason)"
  else
    echo "[budget-revert-check] 한도 이미 기본값($DEFAULT) ($reason)"
  fi
  rm -f "$MARKER"
  # 한도가 바뀌었거나 elevation 마커를 정리하는 경우, 외부 ceiling(gemini 쿼터)도 수렴시킨다.
  # 쿼터 복귀 실패 시 pending 플래그를 남겨 다음 실행에서 재시도(fail-closed; 마커 삭제와 무관하게 수렴 보장).
  if [ "$CUR" != "$DEFAULT" ] || [ "$had_marker" = 1 ]; then
    if revert_gemini_quota; then rm -f "$QUOTA_PENDING"
    else touch "$QUOTA_PENDING"; qmsg=" :warning: gemini 쿼터 복귀 실패(gcloud) — pending 등록, 다음 실행 재시도."; fi
    slack ":white_check_mark: [예산 원복] $reason — 한도 → \$$DEFAULT/day, gemini 쿼터 3000 복귀.${qmsg}"
  fi
  return 0
}

# --- (A) 마커 없음 → 평상 상태: 유한 기본값 보장 ---
if [ ! -f "$MARKER" ]; then
  revert_to_default "활성 elevation 없음(평상 상태)"; exit 0
fi

# --- 마커 파싱 + limit 숫자 검증(손상/임의수정 → BAD) ---
read -r AGE_H TTL_H LIMIT MARKER_OK <<< "$(python3 - "$MARKER" "$MAX_HOURS" <<'PY'
import sys, json, time
try:
    m = json.load(open(sys.argv[1])); maxh = float(sys.argv[2])
    age = (time.time() - float(m.get("created_epoch", 0))) / 3600.0
    ttl = min(float(m.get("hours", maxh)), maxh)
    lim = str(m.get("limit", "?")); float(lim)   # limit 숫자 검증; 실패하면 except
    print(f"{age:.2f} {ttl:.2f} {lim} OK")
except Exception:
    print("999999 0 ? BAD")
PY
)"
AGE_H="${AGE_H:-999999}"; TTL_H="${TTL_H:-0}"; LIMIT="${LIMIT:-?}"; MARKER_OK="${MARKER_OK:-BAD}"

# --- (B) 마커 손상/limit 비정상 → 안전 원복 ---
if [ "$MARKER_OK" != "OK" ]; then
  revert_to_default "elevation 마커 손상/비정상 limit — 안전 원복"; exit 0
fi
# --- (B) 시간 조건: AGE>=TTL(=num_le TTL AGE) → 원복 ---
if num_le "$TTL_H" "$AGE_H"; then
  revert_to_default "elevation TTL 만료(${AGE_H}h ≥ ${TTL_H}h)"; exit 0
fi

# --- throughput/백로그 조회 (DB 오류와 genuine-0 구분) ---
read -r DBSTAT PHYS EDU PEND RECENT <<< "$(python3 - "$RECENT_HOURS" <<'PY'
import sys
try:
    from core.database import execute_query as q
    rh = int(float(sys.argv[1]))
    phys=q("SELECT count(*) c FROM filtered_signals fs LEFT JOIN refined_outputs ro ON ro.filtered_signal_id=fs.id WHERE ro.id IS NULL AND COALESCE(fs.domain,'physical_ai')='physical_ai'",fetch=True)[0]["c"]
    edu=q("SELECT count(*) c FROM filtered_signals fs LEFT JOIN refined_outputs ro ON ro.filtered_signal_id=fs.id WHERE ro.id IS NULL AND fs.domain='edu_consulting'",fetch=True)[0]["c"]
    pend=q("SELECT count(*) c FROM raw_signals WHERE status='pending'",fetch=True)[0]["c"]
    recent=q(f"SELECT count(*) c FROM refined_outputs WHERE created_at >= now() - interval '{rh} hours'",fetch=True)[0]["c"]
    print("OK", phys, edu, pend, recent)
except Exception:
    print("ERR 0 0 0 0")
PY
)"
DBSTAT="${DBSTAT:-ERR}"; PHYS="${PHYS:-0}"; EDU="${EDU:-0}"; PEND="${PEND:-0}"; RECENT="${RECENT:-0}"

# --- DB 조회 실패: throughput으로 판단하지 않는다(정상 장기작업 오인 차단). TTL이 backstop. ---
if [ "$DBSTAT" = "ERR" ]; then
  echo "[budget-revert-check] DB 조회 실패 — throughput 판단 보류, TTL(${AGE_H}h/${TTL_H}h)로만 관리"
  slack ":warning: [budget-revert-check] DB 조회 실패로 throughput 평가 불가. elevation은 TTL로만 관리(자동 만료 대기)."
  if [ "$CUR" != "$LIMIT" ] && is_pos_num "$LIMIT"; then
    if set_env_var DAILY_COST_LIMIT_USD "$LIMIT"; then echo "  한도 재확정 → $LIMIT"
    else slack ":rotating_light: [budget-revert-check] DB오류 경로 한도 재확정($LIMIT) .env 쓰기 실패 — 수동 확인."; fi
  fi
  exit 0
fi
echo "[budget-revert-check] 미정제 physical=$PHYS edu=$EDU / 미필터 pending=$PEND / 최근${RECENT_HOURS}h 정제=$RECENT (한도=$CUR, age=${AGE_H}h/${TTL_H}h)"

# --- (C) throughput 조건: DB 정상인데 최근 창 정제 0건 → outage → 원복 ---
if [ "$RECENT" -le 0 ]; then
  revert_to_default "throughput 정지(최근 ${RECENT_HOURS}h 정제 0건, DB정상) — 무제한 고착 차단"; exit 0
fi
# --- (D) 백로그 조건: 충분히 소진 → 드레인 완료 → 원복 ---
if [ "$PHYS" -lt 500 ] && [ "$EDU" -lt 500 ] && [ "$PEND" -lt 1000 ]; then
  revert_to_default "백로그 소진(physical=$PHYS edu=$EDU pending=$PEND)"; exit 0
fi

# --- 4조건 통과: 정당한 활성 드레인 → elevation 유지. 한도가 (검증된)마커와 다르면 재확정. ---
if [ "$CUR" != "$LIMIT" ] && is_pos_num "$LIMIT"; then
  set_env_var DAILY_COST_LIMIT_USD "$LIMIT" && echo "[budget-revert-check] elevation 재확정: 한도 $CUR → $LIMIT"
fi
echo "[budget-revert-check] elevation 유지(정당한 드레인 진행 중, age=${AGE_H}h/${TTL_H}h, 최근정제=$RECENT)"
