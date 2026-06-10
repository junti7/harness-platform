#!/usr/bin/env bash
# Mac Mini에 "Universe 후보 발굴(unmatched-entity miner) 주1회" launchd 작업을 설치한다.
#
# launchd plist는 머신별 절대경로로 깨지므로(exit 78), 하드코딩하지 않고
# *설치 시점에 Mac Mini에서 실제 경로를 탐지해* plist를 생성한다. [[project_launchd_path_portability]]
#
# 매주 월요일 09:00(KST) mine_universe_candidates.py 실행:
#   → 후보 큐(universe_candidate_queue.*) 갱신
#   → distinct source ≥ 3 후보는 approval_intake.jsonl에 [투자결정]으로 상신(백엔드가 CEO 결재 승격)
# 발굴은 자동, 편입은 게이트(opportunity_approve → seed 편입 → 그 후에도 turtle/legal/capital 별도).
#
# 사용: scripts/install_universe_miner_macmini.sh
set -euo pipefail

SSH_HOST="${MACMINI_SSH_HOST:-macmini}"
REMOTE_REPO="${MACMINI_REPO:-/Users/juntaepark/projects/harness-platform}"
LABEL="com.harness.universe-miner"

# 원격 셸 인젝션 방지: REPO/LABEL에 작은따옴표가 있으면 인라인 따옴표가 깨져 코드 주입 가능 → 차단
case "$REMOTE_REPO$LABEL" in
  *\'*) echo "  ✖ REMOTE_REPO/LABEL에 작은따옴표(')는 허용되지 않습니다. 중단."; exit 1;;
esac

echo "▶ Mac Mini($SSH_HOST)에 Universe miner 주1회 launchd 설치"

ssh -o ConnectTimeout=20 "$SSH_HOST" "REPO='$REMOTE_REPO' LABEL='$LABEL' bash -s" <<'REMOTE'
set -euo pipefail
cd "$REPO"

PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || { echo "  ✖ $PY 없음 — .venv 확인"; exit 1; }
MINER="$REPO/scripts/mine_universe_candidates.py"
[ -f "$MINER" ] || { echo "  ✖ $MINER 없음 — 먼저 배포하세요"; exit 1; }
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
mkdir -p "$HOME/Library/LaunchAgents" "$REPO/logs"

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
    <string>$REPO/scripts/mine_universe_candidates.py</string>
    <string>--lookback-days</string><string>30</string>
    <string>--min-sources</string><string>2</string>
    <string>--promote-min-sources</string><string>3</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$REPO/logs/universe_miner.log</string>
  <key>StandardErrorPath</key><string>$REPO/logs/universe_miner.error.log</string>
</dict>
</plist>
PLISTEOF

launchctl load "$PLIST"
echo "  ✓ 설치: $PLIST (매주 월 09:00)"
REMOTE

echo "▶ 설치 완료"
