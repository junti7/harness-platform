#!/bin/bash
# edu 일일 자족 파이프라인 (프로덕션) — 수집 → 필터 → 정제 → RAG 인덱스
#
# 한 잡이 edu 데이터 흐름 전체를 책임진다(physical_ai 파이프라인과 독립).
#   1) 다양화 DEEP RESEARCH 수집 (rss/scholar/arxiv/openalex/eric/pubmed/hackernews/reddit) → raw_signals
#   2) 맘카페 등 네이버 커뮤니티 수집 (공식 검색 API, ToS 준수) → raw_signals
#   3) Tier2 필터 (Ollama) — 노이즈(광고·무관 글) 제거, edu 관련만 통과
#   4) Tier3 정제(Gemini) + RAG 인덱스 증분 갱신
#
# YouTube는 별도 6시간 잡(run_edu_deep_research)이 raw_signals에 적재하므로,
# 이 잡의 필터 단계가 YouTube 미필터분도 함께 처리한다.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PY=.venv/bin/python

echo "[edu_daily] $(date '+%F %T') 시작"

echo "[edu_daily] 1/4 다양화 DEEP RESEARCH 수집 (학술·커뮤니티·뉴스)"
# Wave 1 (2026-06-09): 그동안 health-recovery 경로(rss,arxiv,scholar)로만 간헐 가동되던
# 다양한 콜렉터를 매일 정규 가동한다. openalex/eric/pubmed/hackernews는 키 불필요 공개 API,
# scholar/rss/arxiv는 기존 검증분. reddit은 OAuth 크레덴셜 없으면 graceful skip.
# youtube는 별도 seamless-gather(연속) 잡이 담당하므로 여기서 제외(중복 부하 방지).
# 채널별 상한: --max-rss-items 30 (정제 백로그 폭주 방지, 수집 ≤ 정제 capacity 원칙).
$PY scripts/run_edu_deep_research.py \
  --sources rss,scholar,arxiv,openalex,eric,pubmed,hackernews,reddit \
  --max-rss-items 30 2>&1 \
  | grep -E "신규 항목|openalex:|eric:|pubmed:|hackernews:|reddit:|scholar:|arxiv:|rss:" || true

echo "[edu_daily] 2/4 네이버 커뮤니티(맘카페) 수집"
$PY scripts/collect_naver_community.py --segment both 2>&1 | grep -E "✅|📥|총" || true

echo "[edu_daily] 3/4 Tier2 필터 (filtered_signals 생성 — 한도 2000)"
# 메인 파이프라인과 동일한 진짜 필터: relevance 점수 + filtered_signals 적재.
# (run_edu_filter.py는 상태만 마킹하고 filtered_signals를 안 만들어 정제로 안 흘렀음)
$PY -c "from adapters.content.filter import filter_signals; n=filter_signals(limit=2000, domain='edu_consulting'); print(f'[필터] filtered_signals 생성 {n}건')" 2>&1 | tail -3 || true

echo "[edu_daily] 4/4 Tier3 정제 + RAG 인덱스"
$PY scripts/run_edu_tier3_parallel.py --workers 4 --shard 0/1 --min-score 0.1 --cost-every 20 2>&1 \
  | grep -E "정제 대상|완료: 정제|RAG 인덱스|일일 비용" || true

echo "[edu_daily] $(date '+%F %T') 완료"
