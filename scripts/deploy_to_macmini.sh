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
#       → 4b) (프론트 변경이면) `npm run build`로 dist 재생성 → 5) origin과 diff=0 검증
#
# 왜 프론트 빌드가 필요한가:
#   프로덕션 프론트는 vite dev 가 아니라 `serve harness-os/frontend/dist`(정적 번들)로 서빙된다.
#   소스만 checkout 하고 dist 를 다시 빌드하지 않으면 화면은 옛 번들 그대로다(2026-06-20 사고).
#   harness-os/frontend/* 가 배포 대상에 있으면 Mac Mini 에서 자동으로 빌드한다. serve 는 파일을
#   매 요청마다 새로 읽으므로 빌드 후 serve 재시작은 불필요하다.
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
REBUILD_FRONTEND="no"
RELOAD_FE_PLIST="no"
RELOAD_BACKEND="no"
for p in "${PATHS[@]}"; do
  case "$p" in core/trading_universe.py|configs/trading/*|scripts/build_trading_universe.py) REBUILD_TRADING="yes";; esac
  # dist 빌드는 프론트 *소스* 변경 시에만(plist 만 바뀐 경우는 빌드 불필요)
  case "$p" in harness-os/frontend/src/*|harness-os/frontend/index.html|harness-os/frontend/public/*|harness-os/frontend/*.json|harness-os/frontend/*.ts|harness-os/frontend/*.js) REBUILD_FRONTEND="yes";; esac
  case "$p" in harness-os/launchd/com.harness.harness-os-frontend.plist) RELOAD_FE_PLIST="yes";; esac
  case "$p" in harness-os/backend/*|harness-os/launchd/com.harness.harness-os-backend.plist) RELOAD_BACKEND="yes";; esac
done

ssh -o ConnectTimeout=20 "$SSH_HOST" "REPO='$REMOTE_REPO' PATHS='$PATHS_STR' REBUILD='$REBUILD_TRADING' REBUILD_FE='$REBUILD_FRONTEND' RELOAD_FE='$RELOAD_FE_PLIST' RELOAD_BE='$RELOAD_BACKEND' bash -s" <<'REMOTE'
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

if [ "${REBUILD_FE:-no}" = "yes" ]; then
  echo "  [4b] 프론트 빌드 (staging dist.tmp → 원자 swap; 실패 시 기존 dist 보존)"
  # 핵심(Red Team 2026-06-20): 실시간 serve 가 읽는 dist 를 in-place 로 비우고 재생성하면
  # ① 빌드 중 부분 산출물/404 ② 빌드 실패 시 dist 손상 위험이 있다. 그래서 dist.tmp 로 빌드하고
  # index.html 생성 확인 후에만 원자에 가깝게 swap 한다. 빌드 실패 시 live dist 는 전혀 건드리지 않는다.
  FE=harness-os/frontend
  rm -rf "$FE/dist.tmp"
  # npm run build = `tsc -b && vite build`; `-- --outDir dist.tmp` 는 vite build 에만 전달됨.
  if ( cd "$FE" && PATH="/opt/homebrew/bin:$PATH" npm run build -- --outDir dist.tmp ) >/tmp/harness_fe_build.log 2>&1 \
       && [ -f "$FE/dist.tmp/index.html" ]; then
    rm -rf "$FE/dist.prev"
    [ -d "$FE/dist" ] && mv "$FE/dist" "$FE/dist.prev"
    mv "$FE/dist.tmp" "$FE/dist"
    # 빌드 provenance 스탬프: check_code_drift.py 가 이 커밋과 origin/main 프론트 소스를 비교해
    # "프론트 변경됐는데 dist 미재빌드(stale)"를 매일 08:00 하드 감지한다.
    git rev-parse origin/main > "$FE/dist/.build_commit" 2>/dev/null || true
    echo "      빌드 OK → $(grep -oE 'index-[^ ]*\.js' /tmp/harness_fe_build.log | head -1) (이전 번들은 dist.prev 로 롤백 보관)"
  else
    rm -rf "$FE/dist.tmp"
    echo "      ✖ 프론트 빌드 실패 — 기존 dist 그대로 보존(화면 영향 없음). 로그 tail:"
    tail -20 /tmp/harness_fe_build.log
    exit 1
  fi
fi

if [ "${RELOAD_FE:-no}" = "yes" ]; then
  echo "  [4c] 프론트 launchd plist 재설치 + reload (serve dist 전환 실제 적용)"
  SERVE_BIN=/opt/homebrew/bin/serve
  if [ ! -x "$SERVE_BIN" ]; then
    echo "      ✖ $SERVE_BIN 없음 — 프론트 정적 서버 의존성 미설치. 'npm i -g serve' 후 재배포. 중단."
    exit 1
  fi
  AGENT="$HOME/Library/LaunchAgents/com.harness.harness-os-frontend.plist"
  sed "s|__ROOT__|$REPO|g" harness-os/launchd/com.harness.harness-os-frontend.plist > "$AGENT"
  UID_N=$(id -u)
  # 레거시 중복 잡(com.harness.frontend, 5월 수동설치)이 5173 을 두고 경쟁하므로 함께 정리
  launchctl bootout "gui/$UID_N/com.harness.frontend" >/dev/null 2>&1 || true
  rm -f "$HOME/Library/LaunchAgents/com.harness.frontend.plist"
  launchctl bootout "gui/$UID_N/com.harness.harness-os-frontend" >/dev/null 2>&1 || true
  sleep 1
  # 5173 을 점유한 잔존 serve(과거 수동 인스턴스)가 있으면 새 agent 가 bind 못 하므로 정리
  for pid in $(pgrep -f "/opt/homebrew/bin/serve" 2>/dev/null || true); do kill -9 "$pid" 2>/dev/null || true; done
  sleep 1
  # bootstrap 만으로 RunAtLoad 가 기동한다(kickstart -k 중복 호출은 더블 인스턴스 레이스를 유발하므로 쓰지 않음).
  launchctl bootstrap "gui/$UID_N" "$AGENT"
  sleep 2
  if lsof -nP -iTCP:5173 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "      ✓ 5173 서빙 중 (serve dist, launchd 관리)"
  else
    echo "      ✖ 5173 미서빙 — 프론트 agent 기동 실패. 로그: logs/harness-os-frontend.error.log. 중단."
    exit 1
  fi
fi

if [ "${RELOAD_BE:-no}" = "yes" ]; then
  echo "  [4d] 백엔드 launchd reload"
  AGENT="$HOME/Library/LaunchAgents/com.harness.harness-os-backend.plist"
  sed "s|__ROOT__|$REPO|g" harness-os/launchd/com.harness.harness-os-backend.plist > "$AGENT"
  UID_N=$(id -u)
  launchctl bootout "gui/$UID_N/com.harness.harness-os-backend" >/dev/null 2>&1 || true
  # bootout 은 비동기 — 서비스가 실제로 사라질 때까지 대기해야 한다. sleep 1 후 bootstrap 하면
  # 'Bootstrap failed: 5: Input/output error' 로 실패하고 백엔드가 내려간 채 남는다(2026-06-21 사고).
  for _i in $(seq 1 20); do
    launchctl print "gui/$UID_N/com.harness.harness-os-backend" >/dev/null 2>&1 || break
    sleep 0.5
  done
  # bootstrap 재시도(EIO 일시 오류 내성)
  for _i in 1 2 3; do
    if launchctl bootstrap "gui/$UID_N" "$AGENT" 2>/tmp/harness_backend_launchctl.log; then break; fi
    sleep 2
  done
  # 실제 서빙(8000) 확인 — launchctl 등록만으로는 부족(기동 실패해도 loaded 일 수 있음).
  be_ok=0
  for _i in $(seq 1 24); do
    if curl -s -o /dev/null --max-time 3 http://127.0.0.1:8000/ 2>/dev/null; then be_ok=1; break; fi
    sleep 1
  done
  if [ "$be_ok" = "1" ]; then
    echo "      ✓ backend 재기동 완료(8000 서빙)"
  else
    echo "      ✖ backend 8000 미서빙 — 기동 실패. 로그: logs/harness-os-backend.error.log / launchctl:"
    tail -20 /tmp/harness_backend_launchctl.log 2>/dev/null || true
    exit 1
  fi
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
