# Wave 2 Collection Expansion — Gate Decision Record

- 날짜: 2026-06-09
- 대상(target_type): `data_collection_policy_change` — physical_ai DEEP RESEARCH 다양화 수집 활성화
- 산출물: `scripts/run_physical_deep_research.py` (신규), `scripts/run_edu_deep_research.py` `save_signal()` (abstract 매핑 수정), `run_pipeline.py` (Tier 1b 통합)
- 관련 계획: `docs/operations/COLLECTION_DIVERSIFICATION_PLAN.md` (Wave 2)

## 변경 요약

physical_ai 도메인은 그동안 RSS(arXiv 카테고리 피드/IEEE/MIT/TechCrunch) + data.go.kr API만 수집했다. 검증된 edu 콜렉터(semantic scholar / openalex / hackernews / 키워드 arXiv)를 physical_ai 주제(휴머노이드·HBM·실리콘 포토닉스·데이터센터 냉각·자율주행 등)로 재사용해 기술 도메인 수집 다양성을 확장한다. 트레이딩 유니버스의 학술 evidence 강화에도 직결.

## red_team_clear ✅ (Claude + Codex, 서로 다른 LLM 2개)

- 1차 Codex verdict: **BLOCK** — 학술 콜렉터가 본문을 `abstract` 키에 저장하나 Tier2 `filter_signals()`는 `summary`/`full_content`만 읽어 학술 시그널이 **제목만으로 채점**됨. (Wave 1 edu 학술 콜렉터에도 동일 영향 — openalex/semantic_scholar/eric)
- 수정: `save_signal()` 중앙 지점에서 `abstract` → `summary`(JSON) + `full_content`(컬럼) 매핑 추가(양쪽 공란일 때만). 전 콜렉터(edu+physical) 일괄 적용.
- 2차 Codex verdict: **CLEAR**.
- Claude(오케스트레이터) 분석: 모듈 전역 오버라이드(`R.DOMAIN`/`R.SCHOLAR_QUERIES_EN_ONLY`/`R.ARXIV_QUERIES`)는 런타임에 읽혀 정상 적용. physical/edu 러너는 **별도 프로세스**(launchd/run_pipeline 단일 실행)로 동작하므로 동일 인터프리터 내 전역 누수 없음.
- 비고: Gemini 선불 크레딧 소진(429) + Claude API 미과금으로 정례 3모델(Claude+Gemini+Codex) 중 Gemini 불가. 이벤트 기반 최소 기준(서로 다른 LLM 2개 = Claude+Codex) 충족.

## legal_review_approve ✅ (저위험)

- 추가 소스: OpenAlex(`/works`, CC0), Semantic Scholar Graph API, Hacker News Algolia API, arXiv export API — 전부 공개 HTTP API 메타데이터/abstract. **브라우저 스크래핑·개인정보·페이월 콘텐츠 없음.** 이미 프로덕션 승인된 arXiv/OpenAlex와 동일 저위험 클래스.
- abstract(≤3000자)는 **내부 Tier2 채점용**으로만 저장. 고객-facing 발행은 Tier3 변환 + `qa_clear` 게이트를 거치며 verbatim 재발행 아님.
- 잔여조건: 학술 abstract가 유료 콘텐츠에 **verbatim 재발행**되면 재검토 필요(현재 파이프라인은 변환 처리).

## pre_mortem_approve ✅ (3 worst-case)

| # | 시나리오 | 확률 | 최대손실 | 회복 | 탐지 |
|---|---|---|---|---|---|
| 1 | 백로그 폭증: Tier3 Gemini-429 중 physical 미정제 누적(300+/run) | 중 | $0(Tier1 무료), 정제 지연 | 캡 하향/러너 일시중지 | collection-health + 백로그 모니터 |
| 2 | API rate-limit/ToS 차단: 과도 쿼리로 IP 스로틀 | 저 | 해당 소스 일시 손실 | backoff·빈도↓ | 로그 error율 |
| 3 | abstract verbatim 재발행 저작권 | 저 | takedown/법적 | QA 게이트 차단 | qa_clear + cite 검증 |

완화: 채널 쿼리 상한(~300/run) + 비치명적 try/except + QA 게이트. 전부 저severity·회복가능.

## 잔여 리스크(문서화·수용)

- (a) 모듈 전역 미복원 — 동일 인터프리터 동시실행 시에만 위험. 배포 모델상 별도 프로세스 → 수용.
- (b) Tier1 backlog admission gate 부재 — 쿼리 상한으로 볼륨 한정(~300/run). 추후 backlog 연동 gate는 개선 항목.
- (c) `ON CONFLICT DO NOTHING`이 중복도 'new'로 카운트(통계 인플레, 데이터 정확성엔 무영향) — 공유 함수 기존 동작, 별도 개선 항목.

## 결론

red_team_clear + legal_review_approve + pre_mortem_approve 충족 → physical_ai DEEP RESEARCH 다양화 수집 **활성화 승인**.
