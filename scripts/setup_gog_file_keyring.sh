#!/usr/bin/env bash
# setup_gog_file_keyring.sh
# Mac Mini에서 한 번만 실행 — gog 토큰을 macOS Keychain → 파일 기반 저장소로 이전
# 이후 SSH 세션에서도 Keychain 잠금 없이 gog가 작동합니다.
#
# 사용법:
#   ssh juntaepark@192.168.0.203
#   bash ~/projects/harness-platform/scripts/setup_gog_file_keyring.sh
#
# 또는 MBP에서 원격 실행:
#   ssh juntaepark@192.168.0.203 "bash ~/projects/harness-platform/scripts/setup_gog_file_keyring.sh"
#   (단, OAuth 브라우저 팝업은 Mac Mini 화면에서 열림)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$(dirname "$SCRIPT_DIR")/.env"
GOG_BIN="/opt/homebrew/bin/gog"
GMAIL_ACCOUNT=""

# ── 1. .env 로드 ──────────────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
  while IFS='=' read -r key val; do
    [[ "$key" =~ ^[[:space:]]*# ]] && continue
    [[ -z "$key" ]] && continue
    key="${key// /}"
    val="${val%%#*}"
    val="${val#"${val%%[![:space:]]*}"}"
    val="${val%"${val##*[![:space:]]}"}"
    export "$key=$val"
  done < <(grep -v '^[[:space:]]*#' "$ENV_FILE" | grep '=')
fi

GOG_BIN="${HARNESS_GMAIL_GOG_BIN:-$GOG_BIN}"
GMAIL_ACCOUNT="${HARNESS_GMAIL_ACCOUNT:-}"
KEYRING_BACKEND="${HARNESS_GMAIL_KEYRING_BACKEND:-file}"
KEYRING_PASSWORD="${HARNESS_GMAIL_KEYRING_PASSWORD:-}"

# ── 2. 사전 검사 ──────────────────────────────────────────────────────────────
echo "=== gog file keyring 설정 ==="
echo "gog 경로: $GOG_BIN"
echo "계정: $GMAIL_ACCOUNT"
echo "keyring backend: $KEYRING_BACKEND"
echo ""

if [[ ! -x "$GOG_BIN" ]]; then
  echo "ERROR: gog 바이너리를 찾을 수 없습니다: $GOG_BIN"
  echo "  설치: brew install gog  또는  brew tap nicholaswilde/tap && brew install nicholaswilde/tap/gog"
  exit 1
fi

if [[ -z "$GMAIL_ACCOUNT" ]]; then
  echo "ERROR: HARNESS_GMAIL_ACCOUNT가 .env에 설정되지 않았습니다."
  exit 1
fi

# ── 3. 기존 Keychain 토큰 삭제 시도 ──────────────────────────────────────────
echo "기존 Keychain 토큰을 제거합니다 (실패해도 계속 진행)..."
GOG_KEYRING_BACKEND="$KEYRING_BACKEND" \
GOG_KEYRING_PASSWORD="$KEYRING_PASSWORD" \
  "$GOG_BIN" auth remove "$GMAIL_ACCOUNT" 2>/dev/null || true

# ── 4. file backend로 재인증 ──────────────────────────────────────────────────
echo ""
echo ">>> OAuth 인증 시작 (브라우저가 열립니다) <<<"
echo "    브라우저가 열리지 않으면 터미널에 표시된 URL을 복사해 열어주세요."
echo ""

export GOG_KEYRING_BACKEND="$KEYRING_BACKEND"
export GOG_KEYRING_PASSWORD="$KEYRING_PASSWORD"
export PATH="/opt/homebrew/bin:/usr/bin:/bin:$PATH"

"$GOG_BIN" auth add "$GMAIL_ACCOUNT" --services gmail

# ── 5. 동작 검증 ──────────────────────────────────────────────────────────────
echo ""
echo "인증 완료. 동작 확인 중..."
RESULT=$(
  GOG_KEYRING_BACKEND="$KEYRING_BACKEND" \
  GOG_KEYRING_PASSWORD="$KEYRING_PASSWORD" \
    "$GOG_BIN" gmail search "from:noreply" \
      -a "$GMAIL_ACCOUNT" -j --results-only --gmail-no-send --max 1 2>&1
)

if echo "$RESULT" | python3 -c "import sys,json; data=json.load(sys.stdin); print('OK -', len(data), '건')" 2>/dev/null; then
  echo ""
  echo "✅ 성공! 이제 SSH 세션에서도 Keychain 없이 gog가 작동합니다."
  echo "   설정 파일: ~/.local/share/python_keyring/ 또는 ~/.config/gog/"
else
  echo ""
  echo "⚠ 검증 결과: $RESULT"
  echo "  인증 자체는 완료됐을 수 있습니다. 수동으로 확인해 주세요:"
  echo "  GOG_KEYRING_BACKEND=$KEYRING_BACKEND GOG_KEYRING_PASSWORD='...' gog gmail search 'test' -a $GMAIL_ACCOUNT -j"
fi

# ── 6. Keychain 자동 잠금 해제 (2차 안전망) ──────────────────────────────────
echo ""
echo "--- Keychain 자동 잠금 비활성화 (추가 안전망) ---"
echo "macOS Keychain의 자동 잠금을 해제합니다 (재부팅 후에는 수동 잠금해제 1회 필요)..."
security set-keychain-settings ~/Library/Keychains/login.keychain-db 2>/dev/null && \
  echo "✅ Keychain 자동 잠금 타임아웃 제거 완료." || \
  echo "⚠ Keychain 설정 변경 실패 (권한 문제일 수 있음). 무시하고 계속 사용 가능."

echo ""
echo "=== 설정 완료 ==="
