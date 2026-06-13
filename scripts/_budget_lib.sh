#!/bin/bash
# 공통 예산 유틸 — budget_revert_check.sh / budget_elevate.sh가 source 한다. [AR-053]
# (실행 진입점 아님. source 전용. macOS/Mac Mini 전용: BSD 가정.)
ENVF="${ENVF:-.env}"
LOCK="runtime/.budget_env.lock"
LOCK_STALE_MIN="${BUDGET_LOCK_STALE_MIN:-30}"   # 락 stale 판정(분). hung/crash 잔존 락 회수.
case "$LOCK_STALE_MIN" in
  ''|*[!0-9]*) echo "[budget-lib] BUDGET_LOCK_STALE_MIN='$LOCK_STALE_MIN' 비숫자 → 30 사용" >&2; LOCK_STALE_MIN=30 ;;
esac

# 양수 숫자 검증. 값은 반드시 argv로 전달(코드 인젝션 차단 — 문자열 보간 금지).
is_pos_num() { python3 -c 'import sys
try: sys.exit(0 if float(sys.argv[1])>0 else 1)
except Exception: sys.exit(1)' "${1:-}" 2>/dev/null; }

# a<=b ? (argv 전달, 인젝션 차단). 0=참.
num_le() { python3 -c 'import sys
try: sys.exit(0 if float(sys.argv[1])<=float(sys.argv[2]) else 1)
except Exception: sys.exit(1)' "${1:-}" "${2:-}" 2>/dev/null; }

# env 키 설정: 기존 정의(export/선행공백/중복 포함) 전부 제거 후 canonical 한 줄 append.
# 끝에 '정확히 1줄' + '그 값'인지 검증(silent no-op / 다중정의 방지). 실패 시 비정상 종료코드.
set_env_var() { # $1=KEY $2=VALUE
  local k="$1" v="$2" tmp
  # KEY는 정규식/glob 메타문자 없는 env 식별자만 허용(grep/sed 패턴 안전 보장).
  case "$k" in
    ''|*[!A-Za-z0-9_]*) echo "[budget-lib] set_env_var: 비정상 KEY '$k' 거부" >&2; return 1 ;;
  esac
  tmp="$(mktemp "${ENVF}.XXXXXX")" || return 1
  grep -vE "^[[:space:]]*(export[[:space:]]+)?${k}=" "$ENVF" > "$tmp" 2>/dev/null || true
  printf '%s=%s\n' "$k" "$v" >> "$tmp"
  chmod 600 "$tmp" 2>/dev/null || true
  mv "$tmp" "$ENVF" || { rm -f "$tmp"; return 1; }
  [ "$(grep -Ec "^${k}=" "$ENVF")" = "1" ] && grep -Fxq "${k}=${v}" "$ENVF"
}

# 이 프로세스의 락 소유 토큰: PID:시작초:난수. 난수 포함이라 PID 재사용(wrap-around)으로도
# 토큰이 겹치지 않는다 → 늦게 끝난 이전 owner가 우연히 같은 PID를 가진 새 owner의 락을 못 지운다.
BUDGET_OWNER_TOKEN="$$:$(date +%s 2>/dev/null):${RANDOM}${RANDOM}${RANDOM}"

# portable mkdir 락(+ owner PID 생존검사 + stale 회수). $1=시도횟수(기본1). 성공 0 / 실패 1.
# 죽은 owner는 즉시 회수(crash 후 영구 차단 방지), 살아있지만 hung(>STALE분)이면 회수.
budget_acquire_lock() {
  mkdir -p runtime
  local tries="${1:-1}" i owner lpid
  for ((i=0; i<tries; i++)); do
    if mkdir "$LOCK" 2>/dev/null; then printf '%s' "$BUDGET_OWNER_TOKEN" > "$LOCK/owner" 2>/dev/null; return 0; fi
    owner="$(cat "$LOCK/owner" 2>/dev/null || true)"
    lpid="${owner%%:*}"
    case "$lpid" in ''|*[!0-9]*) lpid="" ;; esac   # 비숫자 PID는 무효 처리
    if [ -n "$lpid" ] && ! kill -0 "$lpid" 2>/dev/null; then
      echo "[budget-lib] 죽은 owner(pid=$lpid) 락 회수" >&2
      rm -rf "$LOCK" 2>/dev/null || true
      mkdir "$LOCK" 2>/dev/null && { printf '%s' "$BUDGET_OWNER_TOKEN" > "$LOCK/owner" 2>/dev/null; return 0; }
    elif find "$LOCK" -maxdepth 0 -mmin +"$LOCK_STALE_MIN" 2>/dev/null | grep -q .; then
      echo "[budget-lib] stale 락 회수(>${LOCK_STALE_MIN}분 잔존)" >&2
      rm -rf "$LOCK" 2>/dev/null || true
      mkdir "$LOCK" 2>/dev/null && { printf '%s' "$BUDGET_OWNER_TOKEN" > "$LOCK/owner" 2>/dev/null; return 0; }
    fi
    sleep 0.5
  done
  return 1
}
# 우리 토큰이 적힌 락만 해제한다. (stale 회수로 owner가 교체됐다면, 늦게 끝난 이전 owner의
#  trap이 새 owner의 락을 지워 상호배제가 깨지는 것을 방지. 토큰=PID:시작:난수로 충돌 불가.)
budget_release_lock() {
  [ "$(cat "$LOCK/owner" 2>/dev/null || true)" = "$BUDGET_OWNER_TOKEN" ] && rm -rf "$LOCK" 2>/dev/null || true
}
