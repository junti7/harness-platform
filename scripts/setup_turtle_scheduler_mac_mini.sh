#!/bin/bash
# Mac Mini에 Turtle Auto Trader launchd 스케줄러 설치
# 실행: bash scripts/setup_turtle_scheduler_mac_mini.sh
# 스케줄: 월~금 22:30 KST (09:30 EDT NYSE 개장)

set -e

PROJECT_DIR="/Users/juntae.park/projects/harness-platform"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
SCRIPT="$PROJECT_DIR/scripts/turtle_auto_trader.py"
PLIST_NAME="com.harness.turtle-auto-trader"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
LOG_DIR="$PROJECT_DIR/docs/reports"

mkdir -p "$LOG_DIR"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>

    <key>ProgramArguments</key>
    <array>
        <string>${VENV_PYTHON}</string>
        <string>${SCRIPT}</string>
        <string>--execute</string>
    </array>

    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>

    <key>StartCalendarInterval</key>
    <array>
        <!-- 월~금 13:30 UTC = 22:30 KST = 09:30 EDT -->
        <dict>
            <key>Weekday</key><integer>1</integer>
            <key>Hour</key><integer>13</integer>
            <key>Minute</key><integer>30</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>2</integer>
            <key>Hour</key><integer>13</integer>
            <key>Minute</key><integer>30</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>3</integer>
            <key>Hour</key><integer>13</integer>
            <key>Minute</key><integer>30</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>4</integer>
            <key>Hour</key><integer>13</integer>
            <key>Minute</key><integer>30</integer>
        </dict>
        <dict>
            <key>Weekday</key><integer>5</integer>
            <key>Hour</key><integer>13</integer>
            <key>Minute</key><integer>30</integer>
        </dict>
    </array>

    <key>StandardOutPath</key>
    <string>${LOG_DIR}/turtle_trader_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/turtle_trader_stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PAPER_TRADING_AUTO_EXECUTE</key>
        <string>true</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>
EOF

echo "✅ plist 생성: $PLIST_PATH"

# 기존 등록 해제 후 재등록
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✅ launchd 등록 완료"
echo ""
echo "스케줄: 월~금 13:30 UTC (22:30 KST / 09:30 EDT)"
echo "실행 모드: --execute (실제 paper 주문)"
echo ""
echo "즉시 테스트 실행 (dry-run):"
echo "  $VENV_PYTHON $SCRIPT"
echo ""
echo "즉시 실행 (execute):"
echo "  $VENV_PYTHON $SCRIPT --execute"
echo ""
echo "스케줄러 중지:"
echo "  launchctl unload $PLIST_PATH"
