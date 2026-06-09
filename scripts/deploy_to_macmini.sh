#!/usr/bin/env bash
# 안전 배포 — origin/main의 최종본을 Mac Mini(프로덕션)에 선택적으로 반영.
#
# 왜 이런 방식인가:
#   Mac Mini 작업트리에는 런타임 산출물 등 dirty 파일이 매우 많아 전체 `git pull`은 위험하다
#   (미커밋 prod 작업을 날릴 수 있음 — 2026-06-09 사고의 원인). 그래서 "지정한 파일만"
#   origin/main에서 checkout 하고, 그 외 작업트리는 절대 건드리지 않는다.
#
# 절차: 0) 로컬 변경 push 확인 → 1) Mac Mini에서 백업 → 2) origin fetch
#       → 3) 지정 경로만 `git checkout origin/main -- <paths>` → 4) (트레이딩이면) universe 재빌드
#       → 5) origin과 diff=0 검증
#
# 사용:
#   scripts/deploy_to_macmini.sh                       # 기본: 트레이딩 코드/config 일습
#   scripts/deploy_to_macmini.sh core/foo.py configs/bar.json   # 임의 경로 지정
#
# 전제: SoT는 origin/main. 배포할 내용은 *반드시 먼저 commit+push* 되어 있어야 한다.
set -euo pipefail

SSH_HOST="${MACMINI_SSH_HOST:-macmini}"
REMOTE_REPO="${MACMINI_REPO:-/Users/juntaepark/projects/harness-platform}"

# 기본 배포 대상 = 트레이딩 종목선정 일습
DEFAULT_PATHS=(
  "core/trading_universe.py"
  "configs/trading/theme_ticker_map.json"
  "configs/trading/negative_ticker_map.json"
  "configs/trading/universe_seed.json"
  "scripts/build_trading_universe.py"
  "scripts/audit_theme_bridge_precision.py"
)
PATHS=("$@")
if [ ${#PATHS[@]} -eq 0 ]; then
  PATHS=("${DEFAULT_PATHS[@]}")
fi

echo "▶ 배포 대상 (${#PATHS[@]}): ${PATHS[*]}"

# 0) 배포 대상이 origin에 push 되어 있는지 확인 (로컬 미커밋/미푸시면 중단)
echo "▶ [0] 로컬 SoT 정합 확인"
git fetch origin -q
for p in "${PATHS[@]}"; do
  if ! git cat-file -e "origin/main:$p" 2>/dev/null; then
    echo "  ✖ origin/main에 '$p' 없음 — 먼저 commit+push 하세요. 중단."
    exit 1
  fi
  if [ -n "$(git diff origin/main -- "$p")" ] || [ -n "$(git status --porcelain -- "$p")" ]; then
    echo "  ✖ 로컬 '$p'가 origin/main과 다름(미커밋/미푸시). 먼저 commit+push 하세요. 중단."
    exit 1
  fi
done
echo "  ✓ 모든 대상이 origin/main과 일치 (배포 가능)"

# 1~5) Mac Mini에서 실행
echo "▶ Mac Mini($SSH_HOST:$REMOTE_REPO) 배포 시작"
PATHS_STR="${PATHS[*]}"
REBUILD_TRADING="no"
for p in "${PATHS[@]}"; do
  case "$p" in core/trading_universe.py|configs/trading/*|scripts/build_trading_universe.py) REBUILD_TRADING="yes";; esac
done

ssh -o ConnectTimeout=20 "$SSH_HOST" "REPO='$REMOTE_REPO' PATHS='$PATHS_STR' REBUILD='$REBUILD_TRADING' bash -s" <<'REMOTE'
set -euo pipefail
cd "$REPO"
read -r -a PATH_ARR <<< "$PATHS"

echo "  [1] 백업"
BK="scratch/pre_deploy_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BK"
for p in "${PATH_ARR[@]}"; do
  if [ -e "$p" ]; then mkdir -p "$BK/$(dirname "$p")"; cp -R "$p" "$BK/$p"; fi
done
echo "      백업: $BK"

echo "  [2] origin fetch"
git fetch origin -q

echo "  [3] 지정 경로만 origin/main으로 checkout"
git checkout origin/main -- "${PATH_ARR[@]}"

if [ "$REBUILD" = "yes" ]; then
  echo "  [4] trading universe 재빌드"
  PYTHONPATH=. .venv/bin/python scripts/build_trading_universe.py --domain physical_ai --skip-ko >/dev/null 2>&1 && echo "      재빌드 OK" || echo "      ⚠️ 재빌드 실패 — 수동 확인 필요"
fi

echo "  [5] origin 정합 검증 (각 0 기대)"
fail=0
for p in "${PATH_ARR[@]}"; do
  n=$(git diff origin/main -- "$p" | wc -l | tr -d ' ')
  echo "      $p: $n"
  [ "$n" != "0" ] && fail=1
done
[ "$fail" = "0" ] && echo "  ✅ 배포 검증 통과" || { echo "  ✖ 일부 파일 불일치"; exit 1; }
REMOTE

echo "▶ 배포 완료"
