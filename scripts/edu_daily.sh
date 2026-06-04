#!/bin/bash
# edu 일일 자족 파이프라인 (프로덕션) — 수집 → 필터 → 정제 → RAG 인덱스
#
# 한 잡이 edu 데이터 흐름 전체를 책임진다(physical_ai 파이프라인과 독립).
#   1) 맘카페 등 네이버 커뮤니티 수집 (공식 검색 API, ToS 준수) → raw_signals
#   2) Tier2 필터 (Ollama) — 노이즈(광고·무관 글) 제거, edu 관련만 통과
#   3) Tier3 정제(Gemini) + RAG 인덱스 증분 갱신
#
# YouTube는 별도 6시간 잡(run_edu_deep_research)이 raw_signals에 적재하므로,
# 이 잡의 필터 단계가 YouTube 미필터분도 함께 처리한다.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python

echo "[edu_daily] $(date '+%F %T') 시작"

echo "[edu_daily] 1/3 네이버 커뮤니티(맘카페) 수집"
$PY scripts/collect_naver_community.py --segment both 2>&1 | grep -E "✅|📥|총" || true

echo "[edu_daily] 2/3 Tier2 필터"
$PY scripts/run_edu_filter.py 2>&1 | tail -3 || true

echo "[edu_daily] 3/3 Tier3 정제 + RAG 인덱스"
$PY scripts/run_edu_tier3_parallel.py --workers 4 --shard 0/1 --min-score 0.1 --cost-every 20 2>&1 \
  | grep -E "정제 대상|완료: 정제|RAG 인덱스|일일 비용" || true

echo "[edu_daily] $(date '+%F %T') 완료"
