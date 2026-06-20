# Handoff — Edu P1 Data Analysis Agent + Customer Simulation Pack (2026-06-15)

> 작성일: 2026-06-15
> 목적: `/clear` 전 fresh start용 인수인계
> 범위: **edu 관련 작업만 포함**
> 제외: IBKR / watchdog / Slack 오탐 이슈

---

## 0. 한 줄 요약

이번 세션에서는 `Edu Query Engine`의 **P1 (Data Analysis Agent)** 구현을 완료했고, red-team 통과 후
**실제 고객 질문 중심 10건 시뮬레이션 MD**까지 만들었습니다.

현재 기준 핵심 산출물은:

- P1 코드 구현
- P1 migration
- P1 테스트 11건
- dry-run 검증 통과
- customer-facing grounded simulation 10건 MD

---

## 1. 구현 완료 범위

### 1.1 P1 Data Analysis Agent

추가 파일:

- [scripts/edu_data_analysis_agent.py](/Users/juntae.park/projects/harness-platform/scripts/edu_data_analysis_agent.py)
- [infra/migrations/2026-06-14_edu_query_engine_p1.sql](/Users/juntae.park/projects/harness-platform/infra/migrations/2026-06-14_edu_query_engine_p1.sql)
- [tests/test_edu_data_agent.py](/Users/juntae.park/projects/harness-platform/tests/test_edu_data_agent.py)

역할:

- `data/edu_research/*`, `data/edu_youtube_transcripts/*`, `evidence_anchors.json` 수집
- 소스별 adapter 정규화
- `edu_knowledge_items` 적재용 공통 스키마 생성
- dedup / validation / DLQ routing
- `pipeline_runs` 감사 기록
- rights metadata 부착
- customer-facing 사용 가능 범위 강제

### 1.2 customer-facing safety

핵심 보강:

- `rights_class`
- `reuse_scope`
- `excerpt_max_chars`
- `verbatim_allowed`

추가로 migration에서 아래 canonical view를 생성:

- `edu_knowledge_items_customer_facing`

의미:

- raw/community/internal-only 데이터는 그대로 쌓되
- 고객-facing retrieval은 별도 predicate를 통과한 행만 쓰게 하는 경계

---

## 2. 이번 세션에서 닫은 주요 리스크

### 2.1 pipeline audit integrity

초기 red-team blocker:

- `pipeline_runs` bootstrap/preflight 실패 시 감사 row가 불완전하게 남을 수 있음

수정:

- bootstrap 단계에서 필요한 `pipeline_runs` 컬럼 존재를 먼저 강제
- `correlation_id` 타입이 text-compatible 인지 검증
- preflight 실패 경로도 기록 가능한 최소 계약을 먼저 확인

### 2.2 DLQ provenance consistency

초기 red-team blocker:

- DLQ 재사용 시 canonical `correlation_id` / `last_seen` 계열 provenance가 약함

수정:

- unresolved upsert 시 canonical `correlation_id`를 최신 run으로 갱신
- migration dedupe 시
  - `first_seen_correlation_id`는 oldest
  - `last_seen_correlation_id`와 top-level `correlation_id`는 newest
  - `occurrence_count`, `last_seen_at` 병합

### 2.3 rights boundary

후속 red-team blocker:

- internal-only third-party content가 base table에 같이 있어 query path 실수 시 외부 노출 가능

수정:

- migration에 `edu_knowledge_items_customer_facing` view 생성
- Python preflight에서 이 view와 predicate 계약이 정확히 맞는지 검증

---

## 3. 검증 결과

### 3.1 unit tests

명령:

```bash
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p 'test_edu_data_agent.py'
```

결과:

- `11 tests`
- `OK`

테스트 범위 예시:

- duplicate RSS dedupe
- bad source file tolerance
- missing source_url validation
- embedding signature mismatch
- anchor rights defaults
- anchor DLQ correlation
- excerpt cap enforcement
- DLQ index contract
- bootstrap correlation_id type check
- DLQ canonical correlation_id update
- customer-facing view contract

### 3.2 dry-run

명령:

```bash
PYTHONPATH=. .venv/bin/python scripts/edu_data_analysis_agent.py --dry-run
```

안정적으로 확인된 수치:

- `input_count=20574`
- `success_count=20569`
- `skipped_count=3`
- `dlq_count=2`
- `adapter_failures=0`

해석:

- ingestion 안정성은 높은 편
- parse-failure 폭주는 없음
- dedup/skips는 소수

---

## 4. red-team 상태

이번 코드 변경은 최종적으로 독립 reviewer 2개 clear를 확보했습니다.

확인된 clear:

- `Gemini`
- `Copilot`

메모:

- Claude CLI는 장문 prompt에서 응답이 자주 멈춰 audit gap이 있었음
- 최종 판단은 사용 가능 reviewer 2개 clear 기준으로 처리

관련 내부 진행 포인트:

- 초기 blocker는 audit path / DLQ provenance / rights boundary였고 전부 remediation 반영됨

---

## 5. 고객 체감용 simulation 산출물

파일:

- [docs/reviews/edu_pilot_simulations/edu_data_analysis_agent_customer_simulations_2026-06-15.md](/Users/juntae.park/projects/harness-platform/docs/reviews/edu_pilot_simulations/edu_data_analysis_agent_customer_simulations_2026-06-15.md)

구성:

- `10 cases`
- 케이스당 `12-turn`
- 실제 고객 질문 형태
- `AS-IS vs P1` 개선 주석 포함
- customer-facing safe evidence bundle 포함

핵심 목적:

- “앵커 몇 개 나열”이 아니라
- follow-up이 길어질 때 P1 데이터가 얼마나 버티는지 보여주는 것

예시 주제:

- 수학 숙제 AI 의존
- AI 진로 불안
- 중학생 챗봇 감정 의존
- 저학년 영어/읽기 앱 결제 판단
- 학교 스크린 타임 균형
- 직장인 커리어 불안
- 예비교사 AI 리터러시
- 글쓰기/수행평가 경계
- 유아에게 AI 설명하기
- 학교 AI 도구 도입 시 부모 질문 리스트

문서 내에서 강조한 P1 개선:

- AS-IS: 일반론 / 짧은 앵커 나열 / follow-up 취약
- P1: normalized retrieval + rights-safe customer-facing rows + multi-source synthesis

---

## 6. 커밋

이번 edu 라인 관련 핵심 커밋:

- `8d3e437` — `Implement edu query engine P1 data analysis agent`
- `4158898` — `Add edu P1 customer-facing simulation pack`

참고:

- 이후 다른 운영/infra 커밋이 추가로 있었을 수 있으나, edu 인수인계 핵심은 위 두 개입니다.

---

## 7. 현재 이어서 볼 만한 다음 작업

우선순위 후보:

1. `P1.5` 기존 코퍼스 provenance 재라벨링 / crosswalk
2. `P2` intent JSON contract + Tier2 classifier
3. `edu_knowledge_items_customer_facing` 실제 query path 연결
4. simulation MD를 기준으로 retrieval evaluator / grounded answer scorer 추가

실무적으로 가장 자연스러운 다음 단계:

- customer-facing retrieval 함수가 실제로 `edu_knowledge_items_customer_facing`만 쓰도록 query layer 구현

---

## 8. 주의사항

- customer-facing 출력은 반드시 `customer_facing view` 기준으로만 사용
- raw community/internal-only 데이터는 그대로 customer output에 섞으면 안 됨
- simulation MD는 실제 production transcript가 아니라 grounded simulation artifact임
- Mac Mini / trading / watchdog 이슈는 이번 handoff 범위 밖임

