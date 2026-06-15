# EDU DB Transparency Plan

> 목적: edu 자료수집 데이터가 DB에 어떻게 쌓이고, 어떤 query path로 customer-facing 결과가 나오는지 black box 없이 운영자가 직접 볼 수 있게 한다.

## 1. 현재 구조

### 1.1 적재 경로

edu raw source는 주로 아래 파일에서 시작한다.

- `data/edu_research/*`
- `data/edu_youtube_transcripts/*`
- `data/edu_research/evidence_anchors.json`

정규화 및 DB 적재 owner는 [scripts/edu_data_analysis_agent.py](/Users/juntae.park/projects/harness-platform/scripts/edu_data_analysis_agent.py) 이다.

핵심 적재 함수:

- `_upsert_knowledge_items()`
- `_write_dlq()`
- `_mark_pipeline_success_in_tx()`
- `_run_db_persist()`

즉, 현재 P1 stack은 아래 순서다.

1. raw file 수집
2. adapter normalize
3. validation / dedup
4. `edu_knowledge_items` upsert
5. 예외는 `dead_letter_queue`
6. 실행 기록은 `pipeline_runs`

### 1.2 핵심 DB 오브젝트

스키마 정의는 [infra/migrations/2026-06-14_edu_query_engine_p1.sql](/Users/juntae.park/projects/harness-platform/infra/migrations/2026-06-14_edu_query_engine_p1.sql) 기준이다.

주요 테이블/뷰:

- `edu_knowledge_items`
  - 정규화된 edu knowledge row
  - source / provenance / rights / segment / quality metadata 포함
- `edu_knowledge_items_customer_facing`
  - customer-facing safe predicate만 통과한 canonical view
- `dead_letter_queue`
  - validation 실패 / source 이상 / unresolved row
- `pipeline_runs`
  - 적재 실행 감사 로그
- `edu_rag_accumulation`
  - 향후 grounded answer 누적용

### 1.3 customer-facing query path

현재 customer-facing retrieval entrypoint는 [harness-os/backend/main.py](/Users/juntae.park/projects/harness-platform/harness-os/backend/main.py) 이다.

핵심 함수 순서:

1. `_edu_query_text()`
2. `_retrieve_evidence_bundle()`
3. `_edu_db_customer_facing_bundle()`
4. 실패 시 `_edu_ranked_matches()` file index fallback

실제 DB query는 `_edu_db_customer_facing_bundle()` 안에서 아래 view를 읽는다.

- `FROM edu_knowledge_items_customer_facing`

즉, 의도상 customer-facing live path는 base table이 아니라 safe view를 읽는다.

## 2. 왜 black box처럼 느껴지는가

현재 부족한 건 기능보다 관측성이다.

1. 운영자가 테이블 구조를 한 장으로 보는 artifact가 없다.
2. 어떤 함수가 어떤 SQL을 치는지 lineage 문서가 없다.
3. live DB에 row count / source mix / rights mix / segment mix를 한 번에 보는 점검 명령이 없다.
4. query path가 fallback 되었는지, DB hit였는지, index hit였는지 운영 화면에서 바로 안 보인다.
5. retrieval 결과가 어떤 rows를 골랐는지 explain artifact가 없다.

## 3. 투명 운영을 위한 최소 레이어

### 3.1 Schema Transparency

운영자는 최소 아래를 언제든 봐야 한다.

- 테이블 목록
- 컬럼명 / 타입 / nullability
- index 목록
- view definition
- row count

권장 구현:

- `scripts/inspect_edu_db.py`
- 출력:
  - `tables`
  - `views`
  - `columns`
  - `indexes`
  - `row_counts`

### 3.2 Query Transparency

운영자는 “이 답변이 왜 이 rows를 골랐는지”를 봐야 한다.

권장 구현:

- retrieval debug script
- 입력:
  - `query`
  - `segment`
  - `k`
- 출력:
  - SQL source (`db_customer_facing` vs `indexed` vs `fallback`)
  - candidate rows
  - ranking score breakdown
  - final selected rows

### 3.3 Data Lineage Transparency

각 knowledge row는 아래 질문에 답해야 한다.

- 이 row는 어느 source file에서 왔는가?
- 왜 `customer_facing`인가?
- 왜 `internal`인가?
- 왜 `fair_excerpt`인가?
- 왜 DLQ로 빠졌는가?

권장 구현:

- `source_ref`, `natural_key`, `provenance`, `rights_class`, `reuse_scope`를 중심으로 lineage lookup
- row 단건 explain command 제공

### 3.4 Audit Transparency

운영자는 최근 적재가 건강한지 바로 봐야 한다.

권장 확인 항목:

- 최근 `pipeline_runs` 20건
- success / failure
- input_count / success_count / skipped_count / dlq_count
- 최근 unresolved `dead_letter_queue`

## 4. 내가 권장하는 운영 방식

### 4.1 Human-readable view

기술자가 아닌 사람도 볼 수 있게 아래 3개를 고정 산출물로 둔다.

1. `edu schema snapshot`
2. `edu latest ingestion health`
3. `edu retrieval explain`

### 4.2 Machine-readable output

동시에 JSON도 남긴다.

- CLI preview용 text/markdown
- automation/agent용 JSON

### 4.3 Black box를 깨는 운영 원칙

1. customer-facing path는 반드시 view 이름까지 드러난다.
2. fallback 발생 시 로그에 mode를 남긴다.
3. row count, source mix, rights mix를 주기적으로 snapshot 한다.
4. 질문 1개를 넣으면 selected evidence rows가 그대로 보이게 한다.
5. 운영자는 DB를 몰라도 “무슨 데이터가 왜 선택됐는지”를 읽을 수 있어야 한다.

## 5. 지금 바로 만들면 좋은 것

우선순위는 아래다.

1. `inspect_edu_db.py`
2. `explain_edu_retrieval.py`
3. `docs/reviews/edu_db_snapshot_YYYY-MM-DD.md`
4. admin/debug endpoint 또는 internal CLI

## 6. 이 작업의 기대효과

이 레이어가 생기면 아래가 가능해진다.

- DB 구조를 코드 뒤지지 않고 바로 이해
- customer-facing 안전 경계가 실제로 지켜지는지 확인
- retrieval 품질 문제를 “데이터 부족”과 “랭킹 문제”로 분리
- handoff 시 black box 감소
- 대표/부대표에게도 설명 가능한 운영 상태 확보
