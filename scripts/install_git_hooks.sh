#!/usr/bin/env bash
# Harness 공유 git 훅 활성화 — repo의 .githooks/ 를 hooksPath 로 설정한다(머신마다 1회).
#
# 기본 .git/hooks 는 버전관리가 안 되고 머신별로 흩어진다. 운영 불변식을 모든 머신/모든
# 에이전트에 동일하게 강제하려면 버전관리되는 .githooks 를 써야 한다.
#
# 사용:
#   scripts/install_git_hooks.sh            # 로컬(MBP/현재 머신)에 적용
#   ssh macmini '.../scripts/install_git_hooks.sh'  # 프로덕션에도 적용
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_ROOT="$(pwd)"

[ -d "$REPO_ROOT/.githooks" ] || { echo "✖ .githooks 디렉토리 없음 — 먼저 deploy/pull"; exit 1; }

chmod +x "$REPO_ROOT/.githooks/"* 2>/dev/null || true
git config core.hooksPath .githooks

echo "✓ core.hooksPath = $(git config core.hooksPath) (repo: $REPO_ROOT)"
echo "  활성 훅:"
ls -1 "$REPO_ROOT/.githooks/" | sed 's/^/    - /'
echo "  검증: origin = $(git remote get-url origin 2>/dev/null || echo '(없음)')"
