#!/usr/bin/env bash
# Mac Mini에 "결재·리뷰 기록 자동 sync" launchd 작업을 설치한다.
#
# launchd plist는 머신별 절대경로로 깨지므로(exit 78), 하드코딩하지 않고
# *설치 시점에 Mac Mini에서 실제 경로를 탐지해* plist를 생성한다.
#
# 매시간 scripts/sync_decision_records.py --slack 실행 →
#   프로덕션에서 생성된 결재(APPROVAL_REQUESTS.json)·핸드오프 로그·red-team 리뷰 산출물을
#   origin/main 으로 ff-push 환원. 라이브 작업트리/코드는 절대 건드리지 않는다(plumbing 합성).
#
# 사용: scripts/install_decision_record_sync_macmini.sh
set -euo pipefail

SSH_HOST="${MACMINI_SSH_HOST:-macmini}"
REMOTE_REPO="${MACMINI_REPO:-/Users/juntaepark/projects/harness-platform}"
LABEL="com.harness.decision-record-sync"

echo "▶ Mac Mini($SSH_HOST)에 결재·리뷰 기록 sync launchd 설치"

ssh -o ConnectTimeout=20 "$SSH_HOST" "REPO='$REMOTE_REPO' LABEL='$LABEL' bash -s" <<'REMOTE'
set -euo pipefail
cd "$REPO"

PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || { echo "  ✖ $PY 없음 — .venv 확인"; exit 1; }
[ -f "$REPO/scripts/sync_decision_records.py" ] || { echo "  ✖ sync_decision_records.py 미배포 — 먼저 deploy"; exit 1; }
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
GUI="gui/$(id -u)"
mkdir -p "$HOME/Library/LaunchAgents" "$REPO/logs"

# 기존 작업 언로드(있으면, 멱등)
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
    <string>$REPO/scripts/sync_decision_records.py</string>
    <string>--slack</string>
  </array>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$REPO/logs/decision_record_sync.log</string>
  <key>StandardErrorPath</key><string>$REPO/logs/decision_record_sync.error.log</string>
</dict>
</plist>
PLISTEOF

launchctl bootstrap "$GUI" "$PLIST"
echo "  ✓ 설치: $PLIST (매시간 + RunAtLoad)"
sleep 3
echo "  --- 최근 로그 ---"
tail -n 12 "$REPO/logs/decision_record_sync.log" 2>/dev/null || echo "  (로그 아직 없음 — 다음 실행 때 기록됨)"
REMOTE
