# Implementation Plan — Edu Pattern Intelligence Engine

Date: 2026-06-11  
Scope: Harness OS `부모/직장인 AI 진단`에 축적되는 Deep Research RAG, 상담 transcript, 운영 observation을 주기적으로 분석해 `AI 시대 인간 고민 패턴`을 구조화하고, 답변 품질·상품화·운영 우선순위에 재투입하는 시스템을 설계한다.

핵심 목적:

- 잠재 고객이 현장에서 반복적으로 겪는 주요 고민을 미리 파악한다.
- 그 고민들에 대해 다른 잡음성 고민보다 훨씬 빠르고 정밀하게 대응할 수 있는 준비 체계를 만든다.
- 고객 만족도를 극대화하되, 이 시스템이 **고정관념 엔진**으로 변질되지 않도록 구조적으로 막는다.
- 제품 사용 후 발생하는 불만/컴플레인성 언급을 강한 개선 신호로 취급해, 차기 유사 답변에서 같은 불만이 반복되지 않게 한다.

## 1. Why This Matters

현재 edu pilot은 이미 다음 자산을 갖고 있다.

- Deep Research 기반 근거 뱅크: `data/edu_research/evidence_bank.json`
- 임베딩 인덱스: `data/edu_research/evidence_index.json`
- 상담 transcript persistence: `edu_customers`, `edu_cases`, `edu_case_turns`, `edu_magic_links`
- 운영 평가 산출물:
  - `docs/reviews/edu_pilot_simulations/*`
  - `runtime/edu_pilot_runtime_events.jsonl`
  - Red Team / transcript export

문제는 이 자산이 아직 `개별 답변 개선`에는 일부 쓰이지만, `사람들이 실제로 무엇에 막히는지`를 구조화한 상위 패턴 레이어로 승격되지는 않았다는 점이다.

Harness의 트레이딩 유니버스가 여러 근거를 가중치 기반으로 종합해 최종 후보를 뽑듯이, edu pilot도 다음을 해야 한다.

1. 고객 고민을 카테고리화한다.
2. 각 고민의 강도, 빈도, 반복성, 미해결성, 전환 신호를 점수화한다.
3. 그 결과를 상담 prompt / 상품 우선순위 / 콘텐츠 기획 / data collection backlog에 다시 반영한다.

## 2. Goal

최종 목표는 `Edu Pattern Intelligence Engine`을 도입해 아래를 가능하게 만드는 것이다.

- 부모/직장인 사용자의 고민을 연령·성별·직업·자녀 학년· 불안 유형별로 패턴화
- `답답함`, `갈망`, `실행 장애`, `지불 의향 신호`를 수치화
- 상담사가 질문하기 전에 높은 확률로 맞는 frame을 제시
- 상품 backlog를 “감”이 아니라 반복적으로 관측된 pain cluster 기준으로 정렬
- 이 패턴 세트를 단발성 insight가 아니라 `주기적 업데이트 자산`으로 운영
- 사용자 불만/컴플레인을 별도 high-priority signal로 흡수해 다음 유사 답변의 품질 저하를 줄임

## 3. Non-Negotiables

- 패턴은 raw customer quote만으로 확정하지 않는다.
- 최종 패턴 승인은 **Fact Check + Red Team**을 통과해야 한다.
- live 답변에 영향을 주는 패턴은 **Fact Check + Red Team + QA + Legal + CEO/VP sign-off** 없이는 runtime에 주입하지 않는다.
- 모델이 그럴듯하게 만든 stereotype은 패턴으로 인정하지 않는다.
- 연령/성별/직업 추정치는 기본적으로 **descriptive analysis 전용**이며, runtime 답변 biasing 입력으로 사용하지 않는다.
- 상담 응답에 재투입되는 패턴은 `확정`, `관찰 중`, `폐기 예정` 상태를 가진다.
- 운영 루프는 1회성이 아니라 정기 배치여야 한다.
- 미성년 자녀 관련 데이터와 민감한 cohort 속성은 **PIPA/legal review 경로**를 먼저 통과해야 한다.
- 목적은 고객 대응 정밀도 향상이지, demographic shortcut으로 사람을 미리 규정하는 것이 아니다.
- complaint / dissatisfaction signal은 일반 feedback보다 높은 우선순위로 재학습·재검토 큐에 들어가야 한다.

## 4. Proposed Architecture

### Layer A. Inputs

수집 원천을 4개로 나눈다.

1. `Deep Research corpus`
   - `evidence_bank.json`
   - `evidence_index.json`
   - `refined_outputs` 중 `edu_consulting`
2. `Live conversation transcripts`
   - `edu_case_turns`
3. `Operator annotations`
   - CEO / VP / Red Team feedback
   - existing observation notes
4. `Simulation / runtime diagnostics`
   - `docs/reviews/edu_pilot_simulations/*`
   - `runtime/edu_pilot_runtime_events.jsonl`
5. `Customer dissatisfaction signals`
   - transcript 내 불만/답답함/오진 지적
   - post-answer complaint note
   - operator-tagged failure cases

### Layer B. Normalized Pattern Facts

신규 canonical record 제안:

- `edu_pattern_facts`
  - `id`
  - `observed_at`
  - `source_type` (`transcript`, `deep_research`, `simulation`, `operator_note`)
  - `segment` (`parent`, `worker`)
  - `cohort_age_band`
  - `gender_hint`
  - `job_family`
  - `child_school_stage`
  - `pain_category`
  - `pain_detail`
  - `desire_category`
  - `friction_type`
  - `complaint_signal`
  - `complaint_type`
  - `dissatisfaction_severity`
  - `urgency_score_raw`
  - `quote_text`
  - `evidence_ref`
  - `confidence`
  - `provenance_json`

이 레이어는 “패턴 후보를 만들기 위한 원자 facts”만 저장한다. 아직 패턴 확정본이 아니다.

추가 규칙:

- `gender_hint`, `job_family`, `child_school_stage`는 가능한 한 **self-stated / explicitly collected** 값만 사용한다.
- inferred demographic 값은 허용하더라도 `confidence`를 강하게 남기고, low-confidence 값은 cohort scoring에서 제외한다.
- `quote_text`는 PII scrub 이후 저장하는 것을 기본값으로 한다.
- complaint / dissatisfaction 표현은 일반 pain fact와 분리 tagging 해 후속 개선 루프에서 우선 소비한다.

### Layer C. Pattern Scoring Engine

신규 batch job 제안:

- `scripts/build_edu_pattern_intelligence.py`

핵심 역할:

1. 최근 window의 `edu_pattern_facts` 집계
2. 동일 pain cluster 병합
3. cluster별 weighted score 계산
4. pattern candidate와 winner list 생성
5. complaint cluster와 answer-failure cluster 별도 생성

제안 score 식:

`pattern_score = frequency * 0.35 + urgency * 0.20 + frustration_intensity * 0.20 + execution_block * 0.10 + cross_source_support * 0.15`

별도 business field:

`monetization_signal_score`

별도 service-quality field:

`complaint_risk_score`

보정 규칙:

- transcript only cluster는 cap 적용
- Deep Research와 live transcript가 함께 지지하면 가산
- operator note만 있는 cluster는 임시 상태
- simulation failure hotspot은 `operational friction`으로 별도 레이어 집계
- `monetization_signal_score`는 별도 보고용이며 `pattern_score` 승격에 직접 사용하지 않는다.
- runtime 주입 이후 수집된 transcript는 **holdout/off-policy 검증 세트**와 분리해 self-reinforcing loop를 막는다.
- `complaint_risk_score`가 높은 cluster는 답변 템플릿 개선과 retrieval gap 보완 대상으로 우선 승격한다.

### Layer D. Approved Pattern Registry

신규 artifact 제안:

- `data/edu_research/pattern_registry.json`

항목 예:

- `pattern_id`
- `status` (`candidate`, `red_team_review`, `approved`, `deprecated`)
- `segment`
- `cohort`
- `pain_summary`
- `what_people_really_mean`
- `blocked_action`
- `desired_outcome`
- `known_failure_modes`
- `supporting_evidence_count`
- `counterevidence_count`
- `last_reviewed_at`
- `expires_at`
- `fact_check_status`
- `red_team_status`
- `qa_status`
- `legal_review_status`
- `human_approval_status`
- `safe_prompt_hints`
- `avoid_response_patterns`

규칙:

- `approved` 패턴은 TTL을 가진다. `expires_at`을 넘기면 자동으로 `candidate` 또는 `review_required`로 강등한다.
- `safe_prompt_hints`는 demographic stereotype이 아니라 질문 프레이밍, uncertainty disclosure, escalation 문구 중심으로만 쓴다.
- `avoid_response_patterns`에는 과거 complaint를 유발한 답변 습관, 과잉 일반화 문구, 공허한 위로 문구를 기록한다.

### Layer E. Runtime Reuse

승인된 패턴만 아래로 투입한다.

1. diagnose opener framing
2. retrieval reranking hints
3. quick reply candidate shaping
4. curriculum prioritization
5. product/content backlog generation
6. complaint recurrence prevention hints

중요:

- runtime에서는 **사용자가 명시적으로 말한 고민, 자녀 학년, 직업 맥락**만 personalization 입력으로 쓴다.
- inferred demographic pattern은 runtime answer biasing에 사용하지 않는다.
- complaint recurrence prevention은 “예전에 이런 유형에서 불만이 났던 답변 습관을 피하라”는 defensive hint로만 사용한다.

## 5. Pattern Taxonomy

초기 분류축 제안:

- Segment
  - parent
  - worker
- Cohort
  - elementary_parent
  - middle_parent
  - highschool_parent
  - office_worker
  - job_seeker
  - career_switcher
- Pain Category
  - dependency_fear
  - academic_integrity_fear
  - career_replacement_fear
  - AI_literacy_gap
  - parenting_conflict
  - decision_paralysis
  - overload_confusion
  - trust_in_answer_gap
- Desire Category
  - realistic_rule
  - conversation_script
  - step_by_step_start
  - comparative_benchmark
  - future_roadmap
  - emotional_reassurance
- Friction Type
  - does_not_know_where_to_start
  - family_conflict
  - cannot_measure_progress
  - tool_choice_overload
  - lacks_confidence
  - lacks_time

## 6. Update Cadence

### Daily

- transcript / runtime / observation ingestion
- evidence bank / evidence index refresh
- candidate fact extraction append

### Weekly

- pattern candidate rebuild
- score recomputation
- top 20 cluster diff report
- candidate → approved review queue 생성
- top complaint cluster / repeated dissatisfaction diff report 생성

### Biweekly

- Red Team + Fact Check gate
- approved registry update
- deprecated pattern pruning

### Monthly

- taxonomy review
- false pattern audit
- product backlog alignment memo

## 7. Fact Check Gate

패턴 확정 전 Fact Check는 최소 3가지를 본다.

1. `live support`
   - 실제 transcript에서 반복 관측되는가
2. `research support`
   - Deep Research / policy / study / community source에 지지 근거가 있는가
3. `counterexample audit`
   - 특정 하위집단에서만 나타나는 현상을 일반화하지 않았는가
4. `sample sufficiency`
   - cohort별 최소 표본 수와 최소 distinct source 수를 만족하는가
5. `independence check`
   - runtime injection 이후 수집된 transcript에만 의존한 self-confirming pattern은 아닌가
6. `complaint recurrence check`
   - 이전에 실패/불만을 유발한 응답 습관이 같은 cluster에서 반복되고 있지 않은가

신규 script 제안:

- `scripts/fact_check_edu_patterns.py`

출력:

- supported
- weakly_supported
- contradicted
- needs_more_data

## 8. Red Team Gate

패턴 확정 전 Red Team은 아래를 공격적으로 본다.

1. stereotype overreach
2. thin-data generalization
3. “우리 고객이 모두 이렇다” 식 과잉 단정
4. monetization wishful thinking
5. 상담 prompt에 넣었을 때 생길 조작/압박/과잉 유도 위험
6. self-fulfilling feedback loop risk
7. inferred demographic personalization risk
8. complaint-prevention 로직이 또 다른 과잉 방어/회피 답변을 만들 위험

규약상 pair:

- MD/doc revision: **Claude + Gemini**

추가 gate:

- runtime 주입 직전에는 `qa_clear`, `legal_review_approve`, CEO/VP confirm을 추가로 요구한다.
- LLM Red Team은 단독 윤리 승인자가 아니며, 인간 승인 대체 수단으로 사용하지 않는다.

신규 artifact 제안:

- `docs/reviews/edu_pattern_intelligence_red_team_YYYY-MM-DD.md`

## 9. Rollout Plan

### Phase 1. Observation Backbone

목표:

- pattern facts를 추출할 수 있는 최소 데이터 파이프 구성

작업:

- `edu_pattern_facts` schema 추가
- PII scrubbing / retention / consent review 설계
- inferred vs self-stated demographic 분리 저장 규칙 추가
- dissatisfaction / complaint tagging rule 추가
- transcript → fact extraction batch
- operator observation append route 추가

### Phase 2. Candidate Scoring

목표:

- weekly batch로 top pattern candidates 생성

작업:

- `build_edu_pattern_intelligence.py`
- candidate JSON/MD outputs
- score formula와 drift diff report

### Phase 3. Gate Layer

목표:

- fact check + red team 없이는 approved registry로 승격되지 않게 함

작업:

- fact-check script
- review checklist
- approval status machine

### Phase 4. Runtime Integration

목표:

- approved pattern만 상담 runtime에 조건부 투입

작업:

- diagnose prompt pre-brief
- retrieval rerank hint
- curriculum selection bias

## 10. Success Metrics

- 상담 transcript에서 “generic / template-like” complaint 비중 감소
- `research·community realism 부족` complaint 감소
- `show_offer` 이후 전환 단계 이탈률 감소
- `first 4 turns` personalization score 상승
- weekly pattern registry coverage 증가
- false pattern rollback rate 추적

## 11. Risks

- 작은 sample을 큰 패턴으로 과장할 위험
- operator intuition이 데이터처럼 위장될 위험
- 특정 성별/연령/직업군 stereotype 위험
- monetization signal과 user pain을 혼동할 위험
- 패턴화가 실제 대화 다양성을 죽일 위험

## 12. Recommendation

바로 제품 런타임에 패턴을 넣지 말고, 다음 순서가 맞다.

1. `edu_pattern_facts`와 weekly candidate build부터 만든다.
2. 2~4주치 observation을 쌓는다.
3. Fact Check + Red Team을 통과한 소수 패턴만 registry에 올린다.
4. 그 approved subset만 diagnose/curriculum prompt에 투입한다.

이 접근이 맞는 이유는, Harness가 원하는 것은 “그럴듯한 persona fiction”이 아니라 `반복 검증 가능한 인간 고민 지도`이기 때문이다.
