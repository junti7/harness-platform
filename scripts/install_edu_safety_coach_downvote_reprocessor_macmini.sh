#!/usr/bin/env bash
# Mac Mini에 EDU safety-coach downvote 자동조치 reprocessor launchd 작업을 설치한다.
#
# 5분마다 미처리 downvote를 찾아:
#   answer_auto_reinforcement_reviewed event 기록
#   safety-coach policy candidate 기록
#
# 사용: scripts/install_edu_safety_coach_downvote_reprocessor_macmini.sh
set -euo pipefail

SSH_HOST="${MACMINI_SSH_HOST:-macmini}"
REMOTE_REPO="${MACMINI_REPO:-/Users/juntaepark/projects/harness-platform}"
LABEL="com.harness.edu-safety-coach-downvote-reprocessor"

echo "▶ Mac Mini($SSH_HOST)에 EDU safety-coach downvote reprocessor launchd 설치"

ssh -o ConnectTimeout=20 "$SSH_HOST" "REPO='$REMOTE_REPO' LABEL='$LABEL' bash -s" <<'REMOTE'
set -euo pipefail
cd "$REPO"

PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || { echo "  ✖ $PY 없음 — .venv 확인"; exit 1; }
[ -f "$REPO/scripts/edu_safety_coach_downvote_reprocessor.py" ] || { echo "  ✖ edu_safety_coach_downvote_reprocessor.py 미배포 — 먼저 deploy"; exit 1; }

PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
GUI="gui/$(id -u)"
mkdir -p "$HOME/Library/LaunchAgents" "$REPO/logs"

launchctl bootout "$GUI/$LABEL" 2>/dev/null || true

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
    <string>$REPO/scripts/edu_safety_coach_downvote_reprocessor.py</string>
    <string>--limit</string>
    <string>100</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$REPO/logs/edu_safety_coach_downvote_reprocessor.log</string>
  <key>StandardErrorPath</key><string>$REPO/logs/edu_safety_coach_downvote_reprocessor.error.log</string>
</dict>
</plist>
PLISTEOF

launchctl bootstrap "$GUI" "$PLIST"
echo "  ✓ 설치: $PLIST (5분마다 + RunAtLoad)"
sleep 3
echo "  --- 최근 stdout ---"
tail -n 12 "$REPO/logs/edu_safety_coach_downvote_reprocessor.log" 2>/dev/null || echo "  (stdout 아직 없음)"
echo "  --- 최근 stderr ---"
tail -n 12 "$REPO/logs/edu_safety_coach_downvote_reprocessor.error.log" 2>/dev/null || echo "  (stderr 없음)"
REMOTE

echo "▶ 설치 완료"
