#!/bin/bash
# Edu Pattern Intelligence 정기 background rebuild (프로덕션)
#
# com.harness.edu-pattern-intelligence LaunchAgent가 30분(StartInterval=1800)마다 호출한다.
# 대표가 관제 화면을 열지 않아도 아래 artifact가 항상 최신 상태로 준비되게 한다.
#   - runtime/edu_pattern_intelligence.json
#   - runtime/edu_pattern_fact_check.json
#   - runtime/edu_pattern_history.jsonl (build가 증분 append)
#
# 두 스크립트 모두 runtime/(gitignore)에만 쓰므로 작업 트리 dirty를 만들지 않는다.
# 비용: 산출물이 작고 계산이 제한적이라 30분 주기는 관측성 대비 부담이 낮다.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python

echo "[edu_pattern] $(date '+%F %T') 시작"

echo "[edu_pattern] 1/2 패턴 인텔리전스 빌드 (--write)"
"$PY" scripts/build_edu_pattern_intelligence.py --write 2>&1 | tail -5 || true

echo "[edu_pattern] 2/2 팩트체크 (--write)"
"$PY" scripts/fact_check_edu_patterns.py --write 2>&1 | tail -5 || true

echo "[edu_pattern] $(date '+%F %T') 완료"
