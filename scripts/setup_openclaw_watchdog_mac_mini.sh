#!/usr/bin/env bash
# Mac Mini OpenClaw 워치독 + 최신 코드 배포 one-shot 스크립트
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_PATH="$HOME/Library/LaunchAgents/com.harness.openclaw-watchdog.plist"
LABEL="com.harness.openclaw-watchdog"

echo "=== 1. git pull ==="
git -C "$PROJECT_ROOT" pull

echo "=== 2. 프론트엔드 빌드 ==="
cd "$PROJECT_ROOT/harness-os/frontend"
npm run build
cd "$PROJECT_ROOT"

echo "=== 3. OpenClaw 워치독 LaunchAgent 설치 ==="
mkdir -p "$HOME/.openclaw/watchdog"

cat > "$PLIST_PATH" << PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.harness.openclaw-watchdog</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${PROJECT_ROOT}/scripts/openclaw_watchdog.sh</string>
  </array>
  <key>StartInterval</key>
  <integer>120</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${HOME}/.openclaw/watchdog/launchd_stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${HOME}/.openclaw/watchdog/launchd_stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>OPENCLAW_BIN</key>
    <string>/opt/homebrew/bin/openclaw</string>
    <key>OPENCLAW_LAUNCHAGENT_LABEL</key>
    <string>ai.openclaw.gateway</string>
    <key>OPENCLAW_GATEWAY_PORT</key>
    <string>18789</string>
  </dict>
</dict>
</plist>
PLIST_EOF

# 이미 로드된 경우 언로드 후 재로드
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"
echo "워치독 LaunchAgent 로드 완료"

echo "=== 4. OpenClaw 게이트웨이 상태 확인 ==="
if pgrep -f "openclaw.*gateway" > /dev/null 2>&1; then
    PID=$(pgrep -f "openclaw.*gateway" | head -1)
    echo "OpenClaw 실행 중 (PID: $PID)"
else
    echo "OpenClaw 미실행 → LaunchAgent로 시작 시도"
    if [ -f "$HOME/Library/LaunchAgents/ai.openclaw.gateway.plist" ]; then
        launchctl kickstart -k "gui/$(id -u)/ai.openclaw.gateway" || true
        sleep 2
    fi
    if pgrep -f "openclaw.*gateway" > /dev/null 2>&1; then
        echo "OpenClaw 시작 완료"
    else
        echo "경고: OpenClaw 시작 실패 - openclaw 설치 확인 필요"
        echo "  설치: brew install antigravityai/tap/openclaw-cli"
        echo "  설정: openclaw service install"
    fi
fi

echo "=== 5. 백엔드 재시동 ==="
launchctl kickstart -k "gui/$(id -u)/com.harness.backend" 2>/dev/null && echo "백엔드 재시동 완료" || echo "백엔드 LaunchAgent 재시동 실패 (수동 확인 필요)"

echo ""
echo "✅ 완료. http://100.97.175.44:8000/settings 에서 OpenClaw 패널 확인"
