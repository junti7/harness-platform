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

echo "[edu_daily] 4/5 Tier3 정제 + RAG 인덱스"
$PY scripts/run_edu_tier3_parallel.py --workers 4 --shard 0/1 --min-score 0.1 --cost-every 20 2>&1 \
  | grep -E "정제 대상|완료: 정제|RAG 인덱스|일일 비용" || true

echo "[edu_daily] 5/5 입문 커리큘럼 freshness — 증분 적재(daily) + 산출(월요일/신규모델 감지 시)"
# 정제 SoT 증분만 분류해 edu_curriculum_evidence 에 upsert(0.x초).
# build 트리거는 stdout 문자열이 아니라 ingest 의 *exit code* 로 판정한다(red-team MAJOR):
#   0=정상, 10=신규 모델/버전 신호 등장(→ 그날 즉시 build 핫픽스), 그 외=실패.
# 실패는 '|| true' 로 묻지 않고 ① 경고 표면화 ② build 스킵 ③ 잡 최종 종료코드로 전파한다
# (red-team BLOCKER: freshness 파이프라인은 조용한 stale 이 최악 실패. 스케줄러가 실패를 알아야 함).
CURRICULUM_FAILED=0
# errexit-safe 캡처: 상위에서 set -e 가 켜져 있어도 ING_RC 를 안전히 받는다.
if PYTHONPATH=. $PY scripts/build_edu_curriculum.py ingest; then ING_RC=0; else ING_RC=$?; fi
if [ "$ING_RC" -ne 0 ] && [ "$ING_RC" -ne 10 ]; then
  echo "[edu_daily] ⚠️ 커리큘럼 ingest 실패(exit=$ING_RC) — evidence 적재 누락 가능. build 스킵"
  CURRICULUM_FAILED=1
elif [ "$(date +%u)" = "1" ] || [ "$ING_RC" -eq 10 ]; then
  # ingest 성공(0/10) 시에만 build. 실패한 evidence 로 canonical 산출물을 갱신하지 않는다.
  if ! PYTHONPATH=. $PY scripts/build_edu_curriculum.py build; then
    echo "[edu_daily] ⚠️ 커리큘럼 build 실패 — 산출물(runtime/edu_curriculum.json) 갱신 안 됨"
    CURRICULUM_FAILED=1
  fi
fi

echo "[edu_daily] $(date '+%F %T') 완료"
if [ "$CURRICULUM_FAILED" -ne 0 ]; then
  echo "[edu_daily] ⚠️ 커리큘럼 단계 실패 — 잡을 비정상 종료(exit 1)로 표면화"
  exit 1
fi
