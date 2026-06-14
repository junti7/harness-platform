# Edu Query Engine & Data Analysis Agent 개발 계획서

> 작성일: 2026-06-14
> 작성: Claude (Codex 비서실장 위임 작업 / 저자)
> 상태: **DRAFT — red_team_clear 전 실행 전면 BLOCK** (CEO 원칙)
> 대표 발의: 2026-06-14 "비용 효율 3-tier 응답 구조 + 강력한 data analysis agent 선행"
> 상위 규약: PLATFORM.md > CLAUDE.md > 본 문서

---

## 0. 목적 (Why)

현재 edu 응답은 **고객 발화마다 LLM이 맥락을 읽고 매번 생성**한다. 모든 연령/성별/직업 계층을
상대하려면 이 구조는 토큰 사용량이 무제한 증가하고, **유료 온보딩이 안 되는 익명 트래픽의 토큰
비용은 전부 손실비용으로 떨어진다.** (CLAUDE.md Success Metric: "LLM 비용 대비 매출 ≥ BEP")

따라서 응답 구조를 **"매번 생성" → "최대한 DB 조회로 즉답, LLM은 꼭 필요할 때만"** 으로 전환한다.
이 전환의 **선행 조건**은 수집된 edu 데이터를 LLM이 가장 효율적으로 활용할 수 있는 **항목화 DB**와,
그 위에서 동작하는 **robust한 Data Analysis Agent**다. CEO 지시: *이 선행 산출물의 완성도가
보장된 뒤에만 다음 단계로 넘어간다.*

본 계획은 이 우선순위를 어겨서 다른 단계를 먼저 짓는 것을 명시적으로 금지한다.

### 이 계획이 개선하는 것 (Product-over-Pipeline Rule 충족)
- **factual trust**: 즉답 경로는 DB의 검증된 항목만 인용 → 환각 표면적 축소
- **paid conversion economics**: 손실 토큰 비용 절감 = BEP 도달 조건 직접 개선
- **artifact quality**: intent JSON contract로 답변 일관성 확보

→ CLAUDE.md "새 인프라는 위 셋 중 하나를 직접 개선할 때만 우선순위" 조건을 충족한다.

---

## 1. 현재 자산 인벤토리 (재발명 금지 — 위에 얹는다)

| 자산 | 위치 | 현재 역할 | 본 계획에서 |
|---|---|---|---|
| `evidence_index.json` (1,803항목, gemini-embedding-001, 768d) | `data/edu_research/` | 의미유사도 RAG 인덱스 | **Tier 3 retrieval 백엔드로 유지** |
| `evidence_bank.json` (19앵커, 일일 refresh) | `data/edu_research/` | 큐레이트 인용 뱅크 ("목록 밖 출처 생성 금지") | **`curated` 인용 SoT**(아래 주) |
| `core/embeddings.py` | — | `embed_query`/`cosine_topk`/`embedding_backend_signature` | 그대로 재사용 |
| RAG 파이프라인 | `harness-os/backend/main.py` `_retrieve_evidence_bundle`외 | 검색+source_kind 균형+저품질 필터 | **Tier 3로 격하·래핑** |
| 수집 원본 28MB/18파일 | `data/edu_research/{date}/` | ERIC·RSS·HN·OpenAlex·SemanticScholar·Reddit·Naver·YouTube raw | **항목화 DB의 입력 소스** |
| DB 테이블 | `infra/migrations/` | `edu_customers/cases/case_turns/case_snapshots/case_offers/magic_links`, `edu_conversation_log`(append-only 원장) | 신규 테이블과 병존 |
| `edu_pattern_intelligence` | `scripts/build_edu_pattern_intelligence.py` | 패턴 마이닝 | intent 분류 학습 신호로 활용 |

**핵심 사실**: 대표님이 그리신 3-tier 중 **Tier 3(LLM 자연어 → RAG)는 부분 존재**한다.
비어 있는 것은 ① 항목화 DB ② Tier 1 classifier 즉답 ③ Tier 2 intent JSON→DB 조회 ④ 누적 학습 루프다.
본 계획은 기존 RAG를 **교체하지 않고** 그 앞단에 Tier 1/2를 얹어 LLM 호출 자체를 줄인다.

**인용 SoT 분리(Codex r1 MINOR 반영)**: 현 진단상 `evidence_bank`는 얇고(19앵커) `evidence_index`엔 noisy
YouTube가 섞여 있다(`docs/handoffs/edu_pilot_diagnosis_2026-06-08.md`). 따라서 SoT를 provenance 등급으로
명확히 분리한다 — **고객-facing 즉답 인용 = `curated`(evidence_bank 유래) 우선**, `collected`(검증된 수집)
차선, `generated`는 인용 금지(provenance enum = `collected|curated|generated` 3값, `derived` 미사용).
`evidence_index`는 의미검색 후보 풀일 뿐 인용 신뢰등급의 SoT가 아니다.

---

## 2. 목표 아키텍처 — 3-Tier 응답 라우터

```
고객 질의
   │
   ▼
[Tier 1] Rule/Classifier (LLM 미호출, 0토큰)
   │  ├─ 단순·결정형 질의 → 항목화 DB 직접 조회 → 즉답
   │  └─ 분류 불가/맥락 필요 ──────────┐
   ▼                                    │
[Tier 2] LLM 경량 호출 (저비용 모델)    │
   │  맥락 분석 → 합의된 intent JSON 산출 (key/value)
   │  Tier 1이 JSON으로 DB 재조회
   │  ├─ DB hit → 즉답(생성 최소화)
   │  └─ DB miss ──────────────────────┐
   ▼                                    │
[Tier 3] LLM 자연어 해석 (기존 RAG)     │
   │  evidence_index 검색 + 자연어 합성 → 답변
   ▼
[누적 루프] 답변 + 근거 + provenance → 검증 게이트 → DB에 RAG data로 적재
```

### Tier별 책임 경계
- **Tier 1 (classifier)**: LLM 호출 없음. ① 결정형/사실형 질의(예: "지금 몇 시", "이 단계 가격",
  "다음 스텝이 뭐였지") ② intent JSON을 받은 뒤의 **고정 resolver 함수** 호출·렌더링. **분류 신뢰도
  임계값 미만이면 즉답하지 않고 Tier 2로 넘긴다(과신 금지).**

### 고객-facing 데이터 접근 경계 (PII 분리 — Codex red-team r1 BLOCKER 반영)
3-tier 응답 경로가 접근할 수 있는 데이터를 **물리적으로 2등급으로 분리**한다. LLM은 테이블명을 만들 수 없다.

| 등급 | 대상 | 접근 주체 | 인증 | AR-044 |
|---|---|---|---|---|
| **공개 지식** | `edu_knowledge_items` 중 **servable predicate**(아래 고정) 통과 행 | Tier 1/2/3 모두 | 불필요(익명 가능) | 무관(비PII) |
| **케이스/PII** | `edu_cases`, `edu_case_turns`, `edu_conversation_log`, `edu_customers` | **인증된 case 소유자 본인 컨텍스트의 고정 resolver만** | magic_link/세션 필수 + **소유권(case_id ownership) 검증** | **AR-044 hold 종속** |

- 고객-facing 즉답(Tier 1)은 **공개 지식 등급에서만** 근거를 가져온다. **`edu_cases`/PII는 LLM이 만든
  `db_query_hint`로 절대 조회하지 않는다.** "다음 스텝이 뭐였지" 같은 case 참조는 인증 세션에 바인딩된
  `resolve_my_case_progress(authed_case_id)` 고정 함수로만 처리하며, LLM은 함수 호출 여부만 결정한다.
- 이 경계가 코드로 강제되기 전에는 case/PII를 응답 경로에 노출하지 않는다(AR-044 정렬).

**Canonical `servable` predicate (Codex r7 MAJOR 반영 — 구현 편차 차단, 코드 단일 정의)**:
```sql
-- 고객-facing 인용 가능 행 = 아래를 모두 만족(하나라도 불충족 시 즉답 인용 금지)
reuse_scope = 'customer_facing'
AND provenance IN ('collected','curated')          -- generated 제외
AND rights_class IN ('public','fair_excerpt')        -- unknown/internal_only 제외
AND excerpt_max_chars > 0                             -- 인용 허용 길이 양수
AND quality_score >= <임계값(P3에서 baseline 후 확정)>
```
- `verbatim_allowed=false`인 행은 그대로 복붙 금지, `excerpt_max_chars` 이내 발췌 + 출처 표기만 허용.
- 이 predicate는 코드 한 곳(`servable_filter()`)에 고정하고 Tier 1/2/3 모두 이 함수만 통과시킨다.
- **Tier 2 (intent 추출 LLM)**: 저비용 모델(Ollama 로컬 우선, 실패 시 Haiku 급). 자연어 → **고정 스키마
  JSON**. 자유 산문 생성 금지(토큰 절감의 핵심). 출력은 §4 contract로 schema 검증.
- **Tier 3 (생성 LLM)**: DB/intent로 못 풀 때만. 기존 evidence_index RAG 그대로. **여기만 고비용 허용.**

### 비용 게이트 & 측정 지표 (즉답률 단독 금지)
- 각 tier 진입 시 `correlation_id` + tier + 예상/실제 토큰을 `api_cost_log`에 기록(CLAUDE.md Must).
  **단 현재 `api_cost_log`에는 tier/token 컬럼이 없다** → P1에서 마이그레이션 신규(아래 §5.3).
- Tier 2/3 호출은 `DAILY_COST_LIMIT_USD` budget gate를 통과해야 한다.
- **단일 KPI(즉답률) 금지.** 다음을 함께 측정·대시보드화한다(Codex red-team r1 MAJOR 반영):
  - Tier 1 즉답률(LLM 미호출 비율) + **오답률**(false-positive direct answer)
  - tier별 평균/p95 **latency**
  - request당 **token ceiling**(상한 초과 시 강제 Tier 하향 또는 거절)
  - **fallback cascade 비율**(1→2→3 모두 탄 비율 = 최악비용 케이스)
  - **baseline 대비 실제 절감률**(현행 "매번 생성" 대비 토큰/원가 %)
- 위 지표는 P4 통합 전 baseline 측정 → 통합 후 비교가 완료 정의에 포함된다.

---

## 3. 선행 산출물 ① — Data Analysis Agent (GATE: 이게 robust 해지기 전엔 다음 단계 BLOCK)

**역할**: 수집 원본(28MB/18파일, 이종 스키마)을 **DataFrame으로 정규화 → 항목화 → 품질검증 → DB 적재**
하는 재실행 가능 파이프라인. 단발 스크립트가 아니라 **idempotent ETL + 검증 + 관측** 단위.

### 3.1 입력 소스 정규화
- 소스별 어댑터: ERIC / RSS / HackerNews / OpenAlex / Semantic Scholar / Reddit / Naver / YouTube transcript.
- 공통 정규화 스키마(아래 §5 `edu_knowledge_items`)로 매핑. 소스별 필드 차이는 어댑터가 흡수.
- `pandas` DataFrame 중간표현 → 결측/중복/언어/날짜 정규화 → DB upsert.

### 3.2 robustness 요건 (완료 정의, §8과 연동)
1. **Idempotent**: 같은 입력 재실행 시 중복 행 0 (자연키 = `source + source_id` 해시 dedup).
2. **Schema-tolerant**: 신규 소스 필드/누락 필드에 죽지 않음(어댑터 단위 격리, 한 소스 실패가 전체 중단 아님).
3. **Provenance 보존**: 모든 항목에 `source`, `source_url`, `collected_at`, `provenance`(`collected`/`curated`/`generated` 3값).
4. **품질 분류**: 기존 `_edu_is_low_quality_item` 규칙 + source_kind(community/research/media/general) 태깅.
5. **검증 게이트**: 적재 전 필수 필드/길이/언어/임베딩 차원(768) 일치 검사. 실패 행은 DLQ(`dead_letter_queue`)로.
6. **관측**: run마다 입력수/적재수/스킵수/DLQ수/소요시간을 `pipeline_runs`에 기록.
7. **테스트**: `tests/test_edu_data_agent.py` — 정규화·dedup·schema-tolerance·DLQ·idempotency 단위 테스트 ≥ 핵심 경로 커버.

### 3.3 출력
- `edu_knowledge_items`(§5) 적재 + `evidence_index.json`과의 일관성(임베딩 모델/차원 signature 일치).
- 운영 리포트: 적재 통계 + 품질 분포 + 소스별 신선도.

---

## 4. 선행 산출물 ② — Intent JSON Contract (Tier 1↔2 합의 스키마)

Tier 2 LLM은 산문 대신 **고정 JSON만** 출력한다. 초안 스키마(확정 전 red-team 대상):

```json
{
  "intent": "factual_lookup | pricing | next_step | concept_explain | reassurance | offer | smalltalk | unknown",
  "segment": "parent | worker | unknown",
  "entities": {
    "child_grade": "string|null",
    "topic": "string|null",
    "ai_tool": "string|null",
    "concern_category": "dependency_fear | academic_integrity | screen_time | career | ... |null"
  },
  "resolver": "knowledge_search | my_case_progress | static_pricing | none",
  "resolver_args": { "topic": "...|null", "source_kind": "...|null", "keyword": "...|null" },
  "needs_generation": true,
  "confidence": 0.0
}
```

규칙 (Codex red-team r1 BLOCKER/MAJOR 반영 — 테이블명 화이트리스트 폐기):
- **LLM은 테이블명·SQL을 만들지 않는다.** `resolver`는 **사전 정의된 고정 함수 enum 중 하나**만 고른다.
  각 resolver는 자신의 쿼리/테이블/파라미터화를 코드 안에 고정 보유한다(intent별 fixed resolver pattern).
  → "허용된 잘못된 질의(allowed-wrong-query)"와 임의 테이블 접근을 구조적으로 차단.
- `static_pricing`은 **DB 테이블이 아니라 config/static 값**을 반환한다(현 스키마에 `pricing` 테이블 없음 — 가정 제거).
- `my_case_progress`는 **인증 세션의 `authed_case_id`만** 인자로 받고 소유권 검증 후 실행(§2 PII 경계). LLM이 case_id를 주입할 수 없다.
- `resolver_args`는 각 resolver가 자신의 화이트리스트로 검증·파라미터 바인딩(SQL injection 차단은 최소 요건).
- `needs_generation=false` + resolver hit → Tier 1 즉답(Tier 3 미진입).
- `confidence < 임계값` 또는 `intent=unknown` 또는 resolver miss → Tier 3.
- 스키마는 코드에서 강제 검증(잘못된 JSON/임의 key는 unknown 처리, Tier 3 폴백).

---

## 5. DB 설계 — query-efficient 항목화 store (신규 테이블)

기존 테이블과 병존. 핵심 신규: `edu_knowledge_items`(정규화 지식) + `edu_rag_accumulation`(누적 답변).

**기존 테이블 재사용 명시(Codex r7 BLOCKER 반영)**: §3.2/§8이 완료조건으로 쓰는 `dead_letter_queue`,
`pipeline_runs`는 **신규 테이블이 아니라 현행 `infra/schema.sql`의 기존 테이블을 재사용**한다(DDL 추가 없음).
필요한 컬럼이 부족하면 §5.3과 동일하게 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` 마이그레이션으로만 보강하며,
P1 preflight에서 두 테이블 존재/필수 컬럼을 검사해 누락 시 run 중단한다(CLAUDE.md schema preflight Must).

```sql
-- 수집 원본의 정규화·항목화 단일 store (Data Analysis Agent 산출)
CREATE TABLE IF NOT EXISTS edu_knowledge_items (
    id            BIGSERIAL PRIMARY KEY,
    -- 기존 RAG와의 stable crosswalk: evidence_index.json 문자열 id 보존 (Codex r1 BLOCKER 반영)
    source_ref    TEXT,                          -- 예: 'anchor-haidt-shortcut' (기존 index item id)
    natural_key   TEXT NOT NULL UNIQUE,          -- 아래 정의(§ natural_key)
    source        TEXT NOT NULL,                 -- 'eric'|'reddit'|'naver'|...
    source_id     TEXT,
    source_url    TEXT,
    source_kind   TEXT NOT NULL DEFAULT 'general_reference'
                  CHECK (source_kind IN ('community_voice','research_policy','media_case','general_reference')),
    -- provenance enum을 DB 레벨에서 강제(문구만이 아니라 구조적 고정 — Codex r6 반영)
    provenance    TEXT NOT NULL DEFAULT 'collected'
                  CHECK (provenance IN ('collected','curated','generated')),
    -- 저작권/ToS 행단위 권리 메타데이터 (Codex r1 BLOCKER 반영)
    rights_class    TEXT NOT NULL DEFAULT 'unknown'
                    CHECK (rights_class IN ('public','fair_excerpt','internal_only','unknown')),
    reuse_scope     TEXT NOT NULL DEFAULT 'internal'
                    CHECK (reuse_scope IN ('customer_facing','internal')),
    excerpt_max_chars INTEGER NOT NULL DEFAULT 0,     -- 고객-facing 인용 허용 길이(0=금지)
    verbatim_allowed  BOOLEAN NOT NULL DEFAULT FALSE,
    segment       TEXT,                          -- 'parent'|'worker'|null
    item_type     TEXT,                          -- '전문가 발언'|'연구'|'커뮤니티'|...
    title         TEXT,
    body          TEXT NOT NULL,
    cite          TEXT,                          -- 인용 가능한 정제 문장
    lang          TEXT NOT NULL DEFAULT 'ko',
    quality_score NUMERIC(5,2) NOT NULL DEFAULT 0,
    keywords      JSONB NOT NULL DEFAULT '[]'::jsonb,
    emb_model     TEXT,                          -- 'gemini-embedding-001'
    emb_dim       INTEGER,                        -- 768 (signature 일치 검증용)
    collected_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_eki_source_kind ON edu_knowledge_items (source_kind);
CREATE INDEX IF NOT EXISTS idx_eki_segment ON edu_knowledge_items (segment);
CREATE INDEX IF NOT EXISTS idx_eki_keywords ON edu_knowledge_items USING GIN (keywords);
CREATE UNIQUE INDEX IF NOT EXISTS idx_eki_source_ref ON edu_knowledge_items (source_ref) WHERE source_ref IS NOT NULL;
-- 고객-facing 즉답 필터 hot-path (Codex r1 MAJOR 반영)
CREATE INDEX IF NOT EXISTS idx_eki_servable ON edu_knowledge_items (reuse_scope, provenance, quality_score DESC);
-- 한국어 keyword/topic 즉답 검색: pg_trgm(설치 가능 시) 또는 tsvector FTS
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_eki_body_trgm ON edu_knowledge_items USING GIN (body gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_eki_cite_trgm ON edu_knowledge_items USING GIN (cite gin_trgm_ops);

-- natural_key 정의 (Codex r1 MINOR 반영): source_id 있으면 sha256(source||'|'||source_id),
-- 없거나 URL 변동/청킹 시 → sha256(source||'|'||normalize(body))[:chunk] content-digest fallback.
-- (Reddit/Naver/YouTube 청킹·source_id 부재·URL 변경에 견딤)

-- Tier 3 답변 누적(RAG 재적재) — 단, provenance='generated', 자동 승격 금지
CREATE TABLE IF NOT EXISTS edu_rag_accumulation (
    id              BIGSERIAL PRIMARY KEY,
    correlation_id  TEXT NOT NULL,
    case_id         BIGINT,
    query_text      TEXT NOT NULL,
    answer_text     TEXT NOT NULL,
    cited_item_ids  JSONB NOT NULL DEFAULT '[]'::jsonb,  -- 근거가 된 edu_knowledge_items.id
    grounded        BOOLEAN NOT NULL DEFAULT FALSE,       -- 근거 인용 존재 여부
    promoted        BOOLEAN NOT NULL DEFAULT FALSE,       -- 검증 통과 후 지식으로 승격됐는지
    verified_by     TEXT,                                 -- 'qa_clear'|'human'|null
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_era_case ON edu_rag_accumulation (case_id);
CREATE INDEX IF NOT EXISTS idx_era_promoted ON edu_rag_accumulation (promoted);
CREATE INDEX IF NOT EXISTS idx_era_corr ON edu_rag_accumulation (correlation_id);
```

### 5.3 `api_cost_log` 마이그레이션 (필수 — Codex r1 MAJOR 반영)
현 `infra/schema.sql`의 `api_cost_log`에는 tier/token/correlation_id 컬럼이 없다(provider만 별도 마이그레이션으로 추가됨).
비용 관측이 본 계획의 핵심이므로 P1에서 다음 마이그레이션을 명시적으로 추가한다:
```sql
ALTER TABLE api_cost_log ADD COLUMN IF NOT EXISTS tier TEXT;            -- 'tier1'|'tier2'|'tier3'
ALTER TABLE api_cost_log ADD COLUMN IF NOT EXISTS correlation_id TEXT;
ALTER TABLE api_cost_log ADD COLUMN IF NOT EXISTS est_tokens INTEGER;
ALTER TABLE api_cost_log ADD COLUMN IF NOT EXISTS actual_tokens INTEGER;
CREATE INDEX IF NOT EXISTS idx_api_cost_log_corr ON api_cost_log (correlation_id);
```
(현행 스키마와 충돌 없으면 위 컬럼 재사용. 배포 전 `scripts/deploy_migration.py` 경로 준수.)

벡터 검색은 현 단계에서 기존 `evidence_index.json`(파일 기반 cosine) 유지. `pgvector` 도입은
운영 데이터로 비용/지연 측정 후 별도 결정(현 단계 비실행, §10).

---

## 6. 누적 학습 루프 — 환각/출처오염 방어 게이트 (**최우선 안전장치**)

대표님 요구: "Tier 3 답변이 묻히지 않고 DB에 RAG data로 쌓인다." 이는 강력하지만
**자기증폭 환각(self-amplifying hallucination)·출처 오염**의 직접적 위험원이다. CLAUDE.md/evidence_bank
규칙("목록 밖 출처 절대 생성 금지", "통계 수치 새로 지어내지 않음")과 충돌하지 않도록 다음을 강제한다.

1. **provenance 격리**: Tier 3 답변은 항상 `provenance='generated'`로만 적재. **collected/curated와 분리.**
2. **즉답 인용 금지**: Tier 1 즉답은 `provenance IN ('collected','curated')`만 인용. generated는 즉답 근거로 못 씀.
3. **승격 게이트**: generated → 지식(knowledge)으로 승격(`promoted=true`)하려면 **qa_clear 또는 human review** 필수.
   자동 승격 절대 금지. 승격 전까지는 통계·집계 신호로만 사용.
4. **grounded 플래그**: 근거 인용 없는 답변(`grounded=false`)은 검색 후보에서 제외.
5. **루프 차단**: generated 항목은 Tier 3 retrieval 후보에서 기본 제외(옵션 in-context도 별도 가중치 하향).

이 게이트가 없으면 누적 루프는 활성화하지 않는다.

### 6.1 기존 코퍼스 provenance 소급 감사 (P1.5 — Codex r1 BLOCKER 반영)
§6는 "앞으로 쌓일 generated"만 격리한다. 그러나 **현재 SoT는 이미 `refined_outputs` 기반 `pipeline`
항목을 `evidence_bank.json`/`evidence_index.json`에 주입**하고 있다(`docs/education/EVIDENCE_FRESHNESS_LOOP.md`,
`scripts/build_edu_evidence_index.py`). 즉 기존 1,803항목에 LLM 파생물이 섞여 있을 수 있어, 신규 격리만으로는
자기증폭 차단이 불완전하다. 따라서 **P1.5에서 기존 코퍼스를 소급 재라벨링**한다:
- `anchor` → `curated`, `pipeline`(refined_outputs 파생) → `generated`로 provenance 매핑(**`derived` 별도값 안 씀 — `generated` 단일 enum으로 고정**, Codex r2 MAJOR 반영).
- `generated`는 즉답 인용 후보에서 제외, 검색 가중치 하향(§6-2/6-5와 동일 규칙). **`derived` 별도값 미사용.**
- 인덱스에 provenance 필드를 추가해 재빌드하고, **재빌드 전후 retrieval 동등성/롤백 절차**를 둔다(§아래 호환성).

---

## 7. 단계별 개발 계획 (순서 = CEO 우선순위)

(LLM 게이트는 모두 canonical `red_team_clear` — 임의 명칭 금지. Codex r1 MAJOR 반영)

| Phase | 산출물 | 완료 게이트 | LLM 게이트 |
|---|---|---|---|
| **P0** | 본 계획서 | `red_team_clear` | `red_team_clear` |
| **P1 (선행·BLOCKING)** | Data Analysis Agent + `edu_knowledge_items` 적재 + `api_cost_log` 마이그레이션(§5.3) + 테스트 | §8 robustness 요건(수치 임계값 포함) 전부 + 적재 통계 검증 | `red_team_clear` (코드 변경) |
| **P1.5** | 기존 코퍼스 provenance 소급 감사·재라벨링·재빌드(§6.1) + crosswalk(`source_ref`) | 재빌드 전후 retrieval 동등성 + 롤백 절차 검증 | `red_team_clear` |
| **P2** | Intent JSON Contract + Tier 2 분류기(저비용/로컬) + 고정 resolver enum | schema 검증 통과율·오분류율 측정 | `red_team_clear` |
| **P3** | Tier 1 classifier + 고정 resolver 즉답 경로 + 비용 측정셋(§2) | 즉답 정확도 + 과신 방지(임계값) + PII 경계(§2) 검증 | `red_team_clear` |
| **P4** | Tier 3 래핑 + 라우터 통합(1→2→3 폴백) | end-to-end 회귀(기존 응답 품질 비열화) + baseline 대비 절감률 측정 | `red_team_clear` |
| **P5** | 누적 루프 + §6 방어 게이트 | 환각/오염 방어 검증, 승격 게이트 동작 | `red_team_clear` + (고객-facing 시) `qa_clear` + (외부 트래픽 시) AR-044 |

**P1이 robust 판정(아래 §8)을 받기 전에는 P1.5/P2 이후를 시작하지 않는다.** (CEO 명시 우선순위)
각 Phase는 commit→push→origin/main→`scripts/deploy_to_macmini.sh` 선택 배포→양쪽 git status 청결까지가 1단위.
**(주의: 배포 SoT 준수는 법무/품질 게이트의 대체물이 아니다 — 별개로 통과해야 한다. Codex r1 MINOR 반영)**

### 7.1 기존 RAG 하위호환·롤백 (P1.5 — Codex r1 BLOCKER 반영)
현행 RAG는 **문자열 `id` + lazy `source_kind` 추론**(`main.py:_load_rag_index`/`_edu_infer_source_kind_from_item`)에
의존한다. 신규 `edu_knowledge_items`(BIGSERIAL)와의 안전한 공존을 위해:
- `edu_knowledge_items.source_ref`에 기존 문자열 id를 1:1 보존(crosswalk). 기존 검색 경로는 변경 없이 동작.
- provenance 매핑표(`anchor→curated`, `pipeline→generated`)를 코드 상수로 고정. **enum은 `collected|curated|generated` 3값으로 닫는다(`derived` 미사용).**
- 인덱스 재빌드는 **새 파일로 빌드 후 원자적 교체 + 직전 파일 백업**(롤백 가능).
- **회귀 판정(정량, Codex r2 MINOR 반영)**: 고정 질의셋 **≥ 50개**(parent/worker 대표 의향), **k=8**.
  재빌드 전후 **top-3 완전일치 = 100%** 그리고 **top-8 Jaccard ≥ 0.95**. 미달 시 **자동 롤백**(백업 파일 복원) + 원인 분석.
- "기존 RAG 보존"은 위 회귀 기준 통과로 증명되기 전까지 완료로 보지 않는다.

---

## 8. Data Analysis Agent "robust" 완료 정의 (P1 게이트)

아래 전부 충족 시에만 P1 완료(=다음 단계 unblock). **각 항목은 수치 임계값으로 판정**(Codex r1 MAJOR 반영 —
"핵심 경로 커버/정상 적재" 같은 주관 문구 금지):
1. ✅ **Idempotent(결정성)**: 전체 28MB 2회 연속 실행 시 적재 행 **diff = 0**, 중복 자연키 **= 0**.
2. ✅ **Schema-tolerant**: 1개 소스 고의 손상 주입 시 해당 소스만 실패하고 **나머지 소스 적재 성공률 100%**(전체 중단 0).
3. ✅ **Provenance/필드 완전성**: source/source_url/collected_at/provenance/rights_class **null 비율 = 0%**.
   (단 `source_url`/`collected_at`는 DDL상 nullable로 두고 **ETL 검증 게이트로 강제**한다 — 외부 소스에 따라
   원천 결측이 있을 수 있어 DDL NOT NULL 대신 적재 전 채움/거부로 처리. Codex r7 MINOR 반영: 의도 명시.)
4. ✅ **Ingest 성공률 ≥ 95%**(전체 입력 레코드 대비), **DLQ 비율 ≤ 5%**, DLQ 사유 코드화.
5. ✅ **검증 게이트**: 불량 행(필드 누락·길이 미달·언어 불일치·임베딩 차원≠768) DLQ 라우팅 — 주입 테스트 **100% 포착**.
6. ✅ **관측 + 처리시간 상한(확정)**: `pipeline_runs`에 입력수/적재수/스킵수/DLQ수/소요시간 기록.
   처리시간 hard ceiling = **임베딩 재계산 제외 전체 재적재 ≤ 10분**, **신규/변경분 임베딩 포함 시 ≤ 30분**
   (28MB 기준, MBP/Mac Mini 동급). 초과 시 P1 미완료. (Codex r2 MAJOR — "N분" 공란 제거)
7. ✅ **임베딩 signature 일치**: gemini-embedding-001/768 불일치 시 **적재 거부**(검증 테스트).
8. ✅ **샘플 정합성 검수**: 무작위 표본(예: 100행) 원본 대비 필드 정확도 **≥ 98%**(수작업/스크립트 대조).
9. ✅ `tests/test_edu_data_agent.py` green(정규화·dedup·schema-tolerance·DLQ·idempotency 경로) + 비저자 cross-LLM `red_team_clear`.

(위 수치는 본 문서에서 모두 확정됐다. baseline 비용 절감률(§2)만 P4에서 측정 비교하며, 이는 P1 unblock 조건이 아니라 P4 게이트다.)

---

## 9. 리스크 & 게이트 매핑

| 리스크 | 내용 | 완화 | 연계 게이트 |
|---|---|---|---|
| 자기증폭 환각 | generated 답변이 근거로 재사용 | §6 provenance 격리·승격 게이트 | qa_clear/human |
| **기존 코퍼스 오염** | evidence_index에 이미 pipeline 파생물 혼입 | §6.1 소급 재라벨링·재빌드 | red_team_clear(P1.5) |
| 출처 오염 | "목록 밖 출처 생성 금지" 위반 | 즉답은 collected/curated만 인용 | CLAUDE.md Must |
| **PII 직접노출 경로** | LLM db_query_hint가 edu_cases 조회 | §2 데이터 등급 분리 + 고정 resolver, case는 인증+소유권 | AR-044 |
| **저작권/ToS(행단위)** | 외부 소스 본문을 고객-facing 인용 | rights_class/excerpt_max_chars/verbatim 규칙, customer_facing 행만 | legal_review_approve |
| **PII / AR-044** | `edu_conversation_log`·누적 답변에 PII. 항목화 DB·RAG 적재가 개인정보 처리 | 누적 루프는 **AR-044 PIPA 게이트와 정렬 전 비활성**. 수집 원본만 P1 대상(개인 식별 최소) | **AR-044 hold 연동** |
| 수집 원본 저작권/ToS | Reddit/Naver/RSS 등 재배포·인용 적법성 | 내부 분석용 한정, 외부 인용은 Legal 검토 | legal_review_approve |
| Tier 1 과신 오답 | classifier가 틀린 즉답 | confidence 임계값 + 미달 시 Tier 2 폴백 | P3 검증 |
| 비용 역전 | Tier 2 LLM 추가가 오히려 비용↑ | 로컬 모델 우선 + 즉답률 KPI 모니터 | api_cost_log |
| Pipeline-over-Product | 유료고객 0인데 인프라 선투자 | 본 계획은 cost/factual-trust 직결로 정당화. 단 P5(누적)는 트래픽 발생 후 가치 | Success Metric |

**AR-044 교차 주의**: 누적 루프(P5)와 PII 항목화는 edu 공개 런칭 컴플라이언스 GATE와 직결된다.
P1~P4(수집 원본·내부 분석)는 진행 가능하나, **P5 고객 대화 누적은 AR-044 close 전까지 외부 트래픽에
활성화하지 않는다**(현재 외부 익명 트래픽 0이라 내부 검증은 가능).

---

## 10. 명시적 비실행 범위 (이번 계획에서 안 함)
- `pgvector` 도입(운영 측정 후 별도 결정)
- 새 외부 데이터 소스 추가(legal_review 대기 중인 소스 포함)
- Tier 2/3 모델 신규 유료 벤더 추가
- 외부 공개 런칭(AR-044 GATE)
- 누적 답변의 자동 지식 승격

---

## 11. red-team 기록

| 라운드 | Gemini | Codex | 비고 |
|---|---|---|---|
| r1 (2026-06-14) | clear (MINOR1) | **block** (BLOCKER4/MAJOR6/MINOR3) | Codex: PII 직접노출 경로·기존 코퍼스 오염·crosswalk 부재·행단위 저작권·비용지표 단일·robust 임계값 부재·resolver화이트리스트 불충분·인덱스 약함·api_cost_log 컬럼 부재·red_team shorthand. **전부 반영** |
| r2 (2026-06-14) | clear | **block** (MAJOR2/MINOR1) | r1 10건 전부 반영 확인. 잔여: `derived`/`generated` 이원화, §8 처리시간 공란, §7.1 회귀 정량화 → **전부 반영** |
| r3 (2026-06-14) | clear | block (MAJOR1: §6.1 derived 잔존) | §8/§7.1 해결 확인, derived 문구 1줄 잔존 → 수정 |
| r4 (2026-06-14) | clear | block (§1 derived 잔존 1줄) | enum 본문 일관성만 미세 잔존 → 수정 |
| r5 (2026-06-14) | clear | block (§3.2 한글 provenance 라벨 불일치 1건) | derived 닫힘 확인. enum 라벨만 통일 → 수정 |
| r6 (2026-06-14) | clear | block (§5 스키마 CHECK 제약 부재) | 텍스트 통일 확인. DB enum 강제 누락 → provenance/rights_class/reuse_scope/source_kind에 CHECK 추가 |
| r7 (2026-06-14) | clear | block (BLOCKER1/MAJOR1/MINOR1) | CHECK 확인. DLQ/pipeline_runs 재사용 명시·servable predicate 고정·source_url nullable 의도 → 전부 반영 |
| r8 (2026-06-14) | **clear** | **clear** (잔여 비차단 MINOR1) | DLQ/pipeline_runs 재사용·servable predicate·nullable 의도 전부 폐쇄 확인 → **✅ red_team_clear** |

- **✅ red_team_clear (2026-06-14)**: 저자(Claude) 아닌 비저자 LLM 2개(Gemini + Codex)가 동일 최종본(r8)에서 clear.
- 잔여 비차단 MINOR: §2 `quality_score` 임계값은 P3 baseline 후 확정(결정 경계 명시, 차단 사유 아님).
- 검토 도구: `scripts/redteam_review.sh <gemini|codex> <ctx>` (read-only 강제). Claude는 저자라 self-review 불가.
- 영속 기록: `docs/reports/llm_outputs/edu_query_engine_plan_redteam_2026-06-14.md`
- 로그: `docs/governance/RED_TEAM_LOG.md` append.

**이 계획은 red_team_clear를 받았다. 단 실제 구현(P1~) 착수는 CEO 우선순위 확인 후 시작한다.**
