#!/bin/bash
# IBKR Client Portal Gateway + Paper Trader 설치 스크립트
# Mac Mini 전용
# 실행 전 수동 준비 사항:
#   1. ~/ibgateway/ 에 clientportal.gw 압축 해제
#   2. IBKR 포털에서 페이퍼 트레이딩 계정 활성화

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JAVA_BIN="/opt/homebrew/opt/openjdk@17/bin/java"
GATEWAY_DIR="$HOME/ibgateway"
PLIST_GATEWAY="$HOME/Library/LaunchAgents/com.harness.ibgateway.plist"
PLIST_TICKER="$HOME/Library/LaunchAgents/com.harness.ibgateway-tickle.plist"

echo "=== 1. Java 확인 ==="
if [ ! -f "$JAVA_BIN" ]; then
    echo "Java 미설치 → 설치 중..."
    export PATH=/opt/homebrew/bin:$PATH
    brew install openjdk@17
fi
"$JAVA_BIN" -version 2>&1 | head -1
echo "✅ Java OK"

echo ""
echo "=== 2. Gateway 파일 확인 ==="
if [ ! -d "$GATEWAY_DIR" ]; then
    echo "[ERROR] $GATEWAY_DIR 디렉토리 없음"
    echo "  다운로드 방법:"
    echo "  1. https://www.interactivebrokers.com/en/trading/ibkr-api.php 접속"
    echo "  2. 'IBKR Web API' → 'Download' 클릭"
    echo "  3. 다운로드한 zip 파일을 Mac Mini에서:"
    echo "     mkdir -p ~/ibgateway && unzip ~/Downloads/clientportal.gw.zip -d ~/ibgateway/"
    exit 1
fi

if [ ! -f "$GATEWAY_DIR/bin/run.sh" ] && [ ! -f "$GATEWAY_DIR/run.sh" ]; then
    echo "[ERROR] Gateway 실행 파일 없음: $GATEWAY_DIR/bin/run.sh"
    echo "  unzip clientportal.gw.zip -d ~/ibgateway/ 재실행 필요"
    exit 1
fi
echo "✅ Gateway 파일 확인"

echo ""
echo "=== 3. conf.yaml 복사 ==="
mkdir -p "$GATEWAY_DIR/root"
cp "$PROJECT_ROOT/configs/ibgateway/conf.yaml" "$GATEWAY_DIR/root/conf.yaml"
echo "✅ conf.yaml 복사 완료 (포트 5001, 페이퍼 트레이딩 모드)"

echo ""
echo "=== 4. LaunchAgent — IB Gateway 자동 시작 ==="
cat > "$PLIST_GATEWAY" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.harness.ibgateway</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${PROJECT_ROOT}/scripts/start_ibgateway.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${GATEWAY_DIR}</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${GATEWAY_DIR}/gateway_stdout.log</string>
  <key>StandardErrorPath</key>
  <string>${GATEWAY_DIR}/gateway_stderr.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>JAVA_HOME</key>
    <string>/opt/homebrew/opt/openjdk@17</string>
    <key>PATH</key>
    <string>/opt/homebrew/opt/openjdk@17/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
PLIST

echo ""
echo "=== 5. LaunchAgent — 세션 Keepalive (1시간마다 tickle) ==="
cat > "$PLIST_TICKER" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.harness.ibgateway-tickle</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PROJECT_ROOT}/.venv/bin/python</string>
    <string>${PROJECT_ROOT}/scripts/ibkr_paper_trader.py</string>
  </array>
  <key>StartInterval</key>
  <integer>3600</integer>
  <key>StandardOutPath</key>
  <string>${GATEWAY_DIR}/tickle.log</string>
  <key>StandardErrorPath</key>
  <string>${GATEWAY_DIR}/tickle_err.log</string>
</dict>
</plist>
PLIST

# LaunchAgent 등록 (Gateway는 수동 로그인 후 활성화)
launchctl unload "$PLIST_TICKER" 2>/dev/null || true
launchctl load "$PLIST_TICKER"
echo "✅ Keepalive LaunchAgent 등록 완료 (1시간마다 tickle)"

echo ""
echo "=== 완료 ==="
echo ""
echo "【다음 수동 단계】"
echo ""
echo "1. IBKR 페이퍼 트레이딩 계정 활성화 (미완료 시)"
echo "   → https://www.ibkr.com 로그인"
echo "   → Settings → Account Settings → Paper Trading Account"
echo "   → 'Create Paper Trading Account' 클릭"
echo "   → 페이퍼 계정 ID/PW 메모 (실계좌와 별도)"
echo ""
echo "2. IB Gateway 시작"
echo "   bash ~/projects/harness-platform/scripts/start_ibgateway.sh &"
echo ""
echo "3. 브라우저에서 2FA 로그인 (최초 1회)"
echo "   → https://localhost:5001"
echo "   → 페이퍼 트레이딩 계정으로 로그인"
echo "   → IBKR Mobile 앱 2FA 승인"
echo ""
echo "4. 연결 테스트"
echo "   source ~/projects/harness-platform/.venv/bin/activate"
echo "   python ~/projects/harness-platform/scripts/ibkr_paper_trader.py"
echo ""
echo "5. Gateway LaunchAgent 활성화 (로그인 확인 후)"
echo "   launchctl load $PLIST_GATEWAY"
