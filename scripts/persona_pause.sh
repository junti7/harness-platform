#!/usr/bin/env bash
# 페르소나 자율 활동 일시정지 토글 (CEO 지시, 2026-06-13).
#
# 정지 대상: 페르소나 LLM 발화/오케스트레이션(scheduled-meetings, #회의실 토론, Jarvis 라우팅,
#            OpenClaw의 전사회의 위임). 거버넌스/청결/watchdog/backup 잡은 영향 없음.
#
# 동작: runtime/persona_pause.flag 생성/삭제. core.persona_state.personas_paused()가 이 파일을
#       메시지마다 fresh 평가하므로 데몬 재시작 불필요. flag 파일은 gitignore(runtime/)됨.
#
# 사용: scripts/persona_pause.sh on|off|status
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLAG="$ROOT/runtime/persona_pause.flag"

case "${1:-status}" in
  on)
    mkdir -p "$ROOT/runtime"
    printf '페르소나 활동 일시정지 중 (CEO 지시 %s) — 지시는 DM으로 OpenClaw에게 주세요.\n' \
      "$(date '+%Y-%m-%d %H:%M')" > "$FLAG"
    echo "✅ 페르소나 활동 정지: ON ($FLAG)"
    ;;
  off)
    rm -f "$FLAG"
    echo "▶️  페르소나 활동 정지: OFF (재개)"
    ;;
  status)
    if [ -f "$FLAG" ]; then
      echo "⏸  PAUSED — $(cat "$FLAG")"
    else
      echo "▶️  ACTIVE (정지 아님)"
    fi
    ;;
  *)
    echo "사용법: $0 on|off|status" >&2
    exit 2
    ;;
esac
