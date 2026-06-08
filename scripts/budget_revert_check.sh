#!/bin/bash
# 임시 무제한 예산 자동 원복 점검 (멱등).
# 매일 launchd로 실행되어 백로그가 충분히 소진됐으면 비용 게이트를 원복한다.
# 이미 원복된 상태(한도=1.00)면 아무것도 하지 않는다(no-op). 맥락: memory project_temp_unlimited_budget.md
set -uo pipefail
cd "$HOME/projects/harness-platform" || exit 1
export PATH="/opt/homebrew/bin:$PATH"
source .venv/bin/activate 2>/dev/null

# 아침 정상화: QA LLM 재활성. gemini-2.5-flash 일일쿼터 outage 동안 QA_LLM_ENABLED=false로
# 둔 경우가 있으므로, 쿼터가 리셋된 시각(이 잡은 10:30 KST 실행) 이후 항상 true로 복원한다.
# (예산 원복 조건과 무관하게 매일 수행 — early-exit 앞에 둔다.)
if grep -q '^QA_LLM_ENABLED=' .env && ! grep -q '^QA_LLM_ENABLED=true' .env; then
  sed -i '' 's/^QA_LLM_ENABLED=.*/QA_LLM_ENABLED=true/' .env
  echo "[budget-revert-check] QA_LLM_ENABLED=true 복원"
fi

CUR=$(grep -E '^DAILY_COST_LIMIT_USD=' .env | cut -d= -f2)
if [ "$CUR" = "1.00" ]; then
  echo "[budget-revert-check] 이미 원복됨(한도=1.00) — no-op"
  exit 0
fi

# 백로그 조회
read -r PHYS EDU PEND <<< "$(python3 - <<'PY'
from core.database import execute_query as q
phys=q("SELECT count(*) c FROM filtered_signals fs LEFT JOIN refined_outputs ro ON ro.filtered_signal_id=fs.id WHERE ro.id IS NULL AND COALESCE(fs.domain,'physical_ai')='physical_ai'",fetch=True)[0]["c"]
edu=q("SELECT count(*) c FROM filtered_signals fs LEFT JOIN refined_outputs ro ON ro.filtered_signal_id=fs.id WHERE ro.id IS NULL AND fs.domain='edu_consulting'",fetch=True)[0]["c"]
pend=q("SELECT count(*) c FROM raw_signals WHERE status='pending'",fetch=True)[0]["c"]
print(phys, edu, pend)
PY
)"
echo "[budget-revert-check] 미정제 physical=$PHYS edu=$EDU / 미필터 pending=$PEND (한도=$CUR)"

slack() { # $1=text
  python3 - "$1" <<'PY' 2>/dev/null || true
import sys
from adapters.content.slack_router import send_slack_route
send_slack_route("ops_incidents", {"text": sys.argv[1]})
PY
}

# 임계: 미정제 physical<500 AND edu<500 AND 미필터<1000 이면 소진으로 판단
if [ "$PHYS" -lt 500 ] && [ "$EDU" -lt 500 ] && [ "$PEND" -lt 1000 ]; then
  echo "[budget-revert-check] 백로그 소진 — 원복 실행"
  sed -i '' 's/^DAILY_COST_LIMIT_USD=.*/DAILY_COST_LIMIT_USD=1.00/' .env
  GP="generativelanguage.googleapis.com"; PROJ="projects/gen-lang-client-0280653202"; UNIT="1/d/{project}/{model}"
  gcloud alpha services quota update --service=$GP --consumer=$PROJ --metric=$GP/generate_content_paid_tier_2_requests --unit="$UNIT" --value=3000 --force 2>&1 | tail -1
  gcloud alpha services quota update --service=$GP --consumer=$PROJ --metric=$GP/generate_content_paid_tier_3_requests --unit="$UNIT" --value=3000 --force 2>&1 | tail -1
  launchctl load "$HOME/Library/LaunchAgents/com.harness.edu-budget-revert.plist" 2>/dev/null
  echo "[budget-revert-check] 원복 완료: 한도=1.00, 쿼터=3000, edu-budget-revert 재가동"
  slack ":white_check_mark: [예산 원복] 백로그 소진(physical=$PHYS edu=$EDU pending=$PEND) — 비용 한도 1.00/쿼터 3000 원복, 자동복원 잡 재가동."
else
  echo "[budget-revert-check] 백로그 잔여 — 무제한 유지(다음 점검에서 재확인)"
fi
