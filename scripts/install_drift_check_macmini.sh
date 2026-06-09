#!/usr/bin/env bash
# Mac Mini에 "코드 드리프트 매일 점검" launchd 작업을 설치한다.
#
# launchd plist는 머신별 절대경로로 깨지므로(exit 78), 하드코딩하지 않고
# *설치 시점에 Mac Mini에서 실제 경로를 탐지해* plist를 생성한다.
#
# 매일 08:00(KST) `check_code_drift.py --slack --quiet` 실행 → drift면 Slack 경보.
#
# 사용: scripts/install_drift_check_macmini.sh
set -euo pipefail

SSH_HOST="${MACMINI_SSH_HOST:-macmini}"
REMOTE_REPO="${MACMINI_REPO:-/Users/juntaepark/projects/harness-platform}"
LABEL="com.harness.code-drift-check"

echo "▶ Mac Mini($SSH_HOST)에 드리프트 점검 launchd 설치"

ssh -o ConnectTimeout=20 "$SSH_HOST" "REPO='$REMOTE_REPO' LABEL='$LABEL' bash -s" <<'REMOTE'
set -euo pipefail
cd "$REPO"

PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || { echo "  ✖ $PY 없음 — .venv 확인"; exit 1; }
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$REPO/logs"

# 기존 작업 언로드(있으면)
launchctl unload "$PLIST" 2>/dev/null || true

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>EnvironmentVariables</key>
  <dict><key>PYTHONPATH</key><string>$REPO</string></dict>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$REPO/scripts/check_code_drift.py</string>
    <string>--slack</string>
    <string>--quiet</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$REPO/logs/code_drift_check.log</string>
  <key>StandardErrorPath</key><string>$REPO/logs/code_drift_check.error.log</string>
</dict>
</plist>
PLISTEOF

launchctl load "$PLIST"
echo "  ✓ 설치: $PLIST (매일 08:00)"
echo "  즉시 1회 테스트 실행:"
launchctl start "$LABEL" || true
sleep 2
tail -n 8 "$REPO/logs/code_drift_check.log" 2>/dev/null || echo "  (로그 아직 없음 — 다음 실행 때 기록됨)"
REMOTE

echo "▶ 설치 완료"
