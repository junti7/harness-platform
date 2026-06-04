#!/bin/bash
# edu 부트스트랩 예산 복원 + 결과 리포트 (1회성, 2026-06-07 예약)
#
# 부트스트랩용으로 올렸던 DAILY_COST_LIMIT_USD($4)를 정상치($1)로 되돌리고,
# edu RAG 코퍼스 현황을 Slack #exec-president-decisions로 보고한 뒤,
# 자기 자신(launchd 잡)을 정리해 재실행되지 않게 한다.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python

echo "[budget-revert] $(date '+%F %T') 시작"

# 1) 예산 복원 $4 → $1
sed -i '' 's/^DAILY_COST_LIMIT_USD=.*/DAILY_COST_LIMIT_USD=1.00/' .env
echo "[budget-revert] $(grep DAILY_COST_LIMIT_USD .env)"

# 2) 결과 집계 + Slack 리포트
$PY - <<'PYEOF' 2>&1 | grep -viE "AFC|tier="
import sys, json
sys.path.insert(0, ".")
from core.database import execute_query as q
edu = q("SELECT count(*) c FROM refined_outputs ro JOIN filtered_signals fs ON fs.id=ro.filtered_signal_id WHERE fs.domain='edu_consulting'", fetch=True)[0]["c"]
nav = q("SELECT count(*) c FROM refined_outputs ro JOIN filtered_signals fs ON fs.id=ro.filtered_signal_id JOIN raw_signals rs ON rs.id=fs.raw_signal_id WHERE rs.source LIKE 'Naver%'", fetch=True)[0]["c"]
backlog = q("SELECT count(*) c FROM filtered_signals fs LEFT JOIN refined_outputs ro ON fs.id=ro.filtered_signal_id WHERE ro.id IS NULL AND fs.domain='edu_consulting' AND fs.score>=0.1", fetch=True)[0]["c"]
try:
    idx = json.load(open("data/edu_research/evidence_index.json"))
    rag = idx.get("count", 0)
except Exception:
    rag = 0
msg = (
    "*[완료보고] edu RAG 부트스트랩 종료 — 예산 정상화*\n\n"
    "대표님, 며칠간의 맘카페 RAG 부트스트랩을 마치고 정제 예산을 $1/day로 복원했습니다.\n\n"
    f"• edu 정제 총: *{edu:,}건*\n"
    f"• 맘카페(네이버) 정제: *{nav:,}건*\n"
    f"• RAG 검색 코퍼스: *{rag:,}건*\n"
    f"• 미정제 백로그: {backlog:,}건 (이후 매일 10:30 $1/day로 점진 소화)\n\n"
    "이제 상담사 근거가 한국 학부모의 실제 언어로 채워졌습니다."
)
try:
    from adapters.content.slack_router import send_slack_route
    send_slack_route("exec_president_decisions", {"text": msg})
    print("[budget-revert] Slack 발송 완료")
except Exception as e:
    print(f"[budget-revert] Slack 발송 실패: {e}")
PYEOF

# 3) 자기 정리 (재실행 방지)
launchctl bootout "gui/$(id -u)/com.harness.edu-budget-revert" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.harness.edu-budget-revert.plist"
echo "[budget-revert] $(date '+%F %T') 완료 — 잡 자기정리"
