# EDU AI Coach Fresh Start Hand-off

작성일: 2026-06-28 KST
작업 위치: `/Users/juntae.park/projects/harness-platform`

## Codex CLI 운영 규칙

사용자가 별도 해제하기 전까지 Codex CLI 응답은 `caveman ultra` 스타일로 짧게 답한다. 단, 코드 변경 요약은 정확하게 유지한다. 변경 파일, 검증, 커밋/배포 상태는 생략하지 않는다.

## 현재 한 줄 상태

EDU AI 코치의 “질문 의도 무시 → 수업 개념 fallback” 문제는 수정/배포 완료. 다만 RAG 출처 표시와 RAG 실제 작동 품질을 외부 LLM으로 전수 평가하려는 다음 단계가 남아 있다.

## 최근 완료 커밋

최신 main:

```text
40eb063 fix: hide edu coach internal fallback badge
7c7bea0 fix: prevent edu coach concept fallback drift
71a1847 docs: audit edu coach corpus union
1d9a5f8 test: expand edu coach corpus union guard
ac688aa test: guard edu coach auto reinforcement health
1e68b6c test: simulate edu coach downvote auto action
cfce52f test: add edu coach structured packet shadow runner
15c367a test: guard edu coach structured packet
```

## 배포 상태

### `7c7bea0`

내용:

- non-concept 질문이 `AI는 큰 이름이고, LLM은...`로 도망가는 문제 수정.
- `너는 특별해`, `부모보다 AI`, `기술을 무서워하지 않을까` 유형 intent fallback 추가.
- corpus를 질문형 quality gate 기준으로 재정제.

검증:

- local: `pytest tests/test_edu_vp_training_flow.py tests/test_edu_coach_simulation_regression_guard.py tests/test_edu_coach_corpus_scenario_generator.py -q`
  - `95 passed`
- local regression:
  - corpus `22,862/22,862 clear`
  - adversarial `378/378 clear`
- Mac Mini remote regression:
  - corpus `22,862/22,862 clear`
  - adversarial `378/378 clear`
  - auto-reinforcement pending `0`
  - latency guard OK

배포:

- Mac Mini backend reload 완료.
- `/api/health` OK.

### `40eb063`

내용:

- edu-app에서 사용자에게 내부 `fallback` badge를 노출하지 않도록 수정.
- `맞는 자료 없음` → `일반 원칙 답변`
- `fallback` → `기본 안전 코치`
- `fast-template` → `빠른 안전 코치`

수정 파일:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`

검증:

- local `npm run build` 통과.
- Mac Mini `harness-os/edu-app` remote `npm run build` 통과.
- remote dist에서 `맞는 자료 없음` 문자열 제거 확인.
- `/api/health` OK.

## 현재 untracked 파일

아래 2개 파일은 아직 커밋되지 않았다.

```text
docs/reviews/edu_coach_simulations/edu_coach_external_llm_evaluation_guide_20260628.md
docs/reviews/edu_coach_simulations/edu_coach_rag_diagnosis_handoff_20260628.md
```

### 1. External LLM Evaluation Guide

경로:

```text
/Users/juntae.park/projects/harness-platform/docs/reviews/edu_coach_simulations/edu_coach_external_llm_evaluation_guide_20260628.md
```

목적:

- 추출된 전체 질문지에 대해 다른 LLM이 답변 품질, RAG 사용 여부, RAG 적합성, RAG 충실성을 평가하게 하는 지침서.

포함:

- 평가 대상 파일 경로
- 질문지 추출 명령
- 외부 LLM evaluator prompt
- `clear / needs_work / block` 판정 기준
- 답변 품질 rubric
- RAG Decision / Fit / Faithfulness rubric
- JSONL 출력 schema
- batch summary schema
- 자동 block 조건

기준 corpus:

- `configs/education/edu_coach_corpus_scenarios.json`
  - `22,862` cases
- `configs/education/edu_coach_adversarial_scenarios.json`
  - `378` cases
- `docs/reviews/edu_coach_simulations/corpus_utterances_20260627T131753Z.jsonl`

### 2. RAG Diagnosis Hand-off

경로:

```text
/Users/juntae.park/projects/harness-platform/docs/reviews/edu_coach_simulations/edu_coach_rag_diagnosis_handoff_20260628.md
```

중요:

- 이 파일은 현재 untracked이고, Codex가 아직 독립 검증하지 않았다.
- 내용상 Claude 또는 외부 진단 세션 산출물로 보인다.
- 다음 세션은 이 문서를 그대로 믿지 말고 재현 검증해야 한다.

주장 요약:

- EDU AI Coach RAG가 거의 작동하지 않는다.
- DB 1차 경로가 `edu_knowledge_items_customer_facing` 테이블 미존재로 실패한다.
- score 검증이 `score < 2.0`으로 되어 있어 cosine score 후보를 모두 reject할 수 있다.
- embedding provider mismatch가 있을 수 있다.
- structured packet flag가 꺼져 있다.
- 검색 `limit=1`, timeout이 작아 근거 다양성이 낮다.

다음 세션에서 해야 할 일:

1. `edu_coach_rag_diagnosis_handoff_20260628.md`의 각 주장 재현.
2. `harness-os/backend/main.py`의 `_edu_vp_validate_safety_coach_evidence`, `_edu_vp_safety_coach_evidence`, `_edu_ranked_matches`, `_edu_db_customer_facing_bundle` 확인.
3. 실제 DB table 존재 여부 확인.
4. `data/edu_research/evidence_index.json`의 provider/model/dimension 확인.
5. 런타임 embedding provider와 index provider 일치 여부 확인.
6. RAG score threshold가 실제로 후보를 과도하게 reject하는지 샘플로 확인.

## 핵심 데이터 파일

```text
configs/education/edu_coach_corpus_scenarios.json
configs/education/edu_coach_adversarial_scenarios.json
docs/reviews/edu_coach_simulations/corpus_utterances_20260627T131753Z.jsonl
docs/reviews/edu_coach_simulations/corpus_coverage_20260627T131753Z.md
```

현재 corpus 구성:

```text
case_count: 22,862
selection_mode: max_quality_question_corpus_union_no_family_quota
source_family_counts:
  naver_blog: 8,069
  naver_cafe: 6,524
  naver_kin: 4,586
  rss: 3,249
  youtube: 402
  evidence_bank: 19
  academic: 6
  reddit: 4
  hackernews: 2
  googleplay: 1
```

## 사용자 문제의 원인 정리

### 문제 1

질문:

```text
부모보다 AI가 아이 말을 더 잘 들어주면 그게 꼭 나쁜 일은 아니지 않아?
```

과거 문제:

- 답이 `AI는 큰 이름이고, LLM은...`로 빠짐.

수정:

- concept fallback은 질문이 현재 개념 정의/차이를 직접 물을 때만 작동.
- 관계 대체/정서 의존 intent는 별도 fallback으로 답함.

현재 답변 성격:

- “꼭 나쁜 일이라고만 볼 필요는 없다.”
- 다만 AI 대화 뒤에 사람 관계와 실제 행동이 좋아지는지 봐야 한다.
- 부모는 AI를 경쟁 상대로 보지 말고 작은 연결을 만든다.

### 문제 2

화면에:

```text
맞는 자료 없음 fallback
```

처럼 표시됨.

확인된 원인:

- `맞는 자료 없음`: RAG 후보가 없거나 부적합해 `evidence_used=false`.
- `fallback`: 내부 엔진 상태명. 사용자는 실패처럼 이해함.

수정:

- UI 표시 문구를 사용자용으로 변경.
- `맞는 자료 없음` → `일반 원칙 답변`
- `fallback` → `기본 안전 코치`

## 평가 지침서 사용법

외부 LLM 평가를 진행하려면 먼저 아래 파일을 읽힌다.

```text
docs/reviews/edu_coach_simulations/edu_coach_external_llm_evaluation_guide_20260628.md
```

이 지침서가 요구하는 평가 입력 JSONL에는 최소 다음 필드가 필요하다.

```json
{
  "case_id": "corpus_0001",
  "question": "...",
  "coach_answer": "...",
  "evidence_used": false,
  "evidence_items": [],
  "evidence_meta": {}
}
```

주의:

- 현재 corpus 파일은 질문지다.
- 답변 품질 평가를 하려면 각 질문에 대해 실제 AI 코치 응답을 생성해 `coach_answer`를 붙여야 한다.
- RAG 평가를 하려면 응답 생성 시 `evidence_used`, `evidence_items`, `evidence_meta`도 함께 저장해야 한다.

## 다음 작업 권장 순서

1. untracked 평가 지침서 검토 후 커밋 여부 결정.
2. untracked RAG 진단 handoff의 주장 재현 검증.
3. 전체 질문지 추출 JSONL 생성.
4. 질문별 실제 AI 코치 답변 + RAG metadata 생성하는 batch script 작성.
5. 외부 LLM evaluator 입력 JSONL 생성.
6. 외부 LLM 평가 실행.
7. 평가 결과 summary에서 block/needs_work/top issue 확인.
8. RAG 결함이 재현되면 P0부터 수정.

## 검증 명령

기존 EDU coach regression:

```bash
.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py tests/test_edu_coach_simulation_regression_guard.py tests/test_edu_coach_corpus_scenario_generator.py -q
.venv/bin/python scripts/check_edu_coach_simulation_regression.py
```

edu-app build:

```bash
cd harness-os/edu-app
npm run build
```

Mac Mini health:

```bash
curl -fsS http://macmini:8000/api/health
```

Mac Mini regression:

```bash
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && .venv/bin/python scripts/check_edu_coach_simulation_regression.py'
```

## 배포 명령 참고

backend/config/scripts 배포 예:

```bash
scripts/deploy_to_macmini.sh harness-os/backend/main.py configs/education/edu_coach_corpus_scenarios.json scripts/check_edu_coach_simulation_regression.py
```

edu-app source 배포 후 remote build:

```bash
scripts/deploy_to_macmini.sh harness-os/edu-app/src/components/TrainingScreen.tsx
ssh macmini 'cd /Users/juntaepark/projects/harness-platform/harness-os/edu-app && PATH="/opt/homebrew/bin:$PATH" npm run build'
```

## 남은 리스크

- 외부 LLM 평가 지침서는 작성됐지만 아직 커밋되지 않았다.
- RAG 진단 handoff는 아직 Codex 검증 전이다.
- RAG가 실제로 충분히 작동하는지는 전체 질문 batch + answer metadata 없이는 확정 불가.
- `evidence_used=false`는 항상 나쁜 것이 아니다. 맞는 근거가 없으면 RAG를 쓰지 않는 것이 맞다. 하지만 맞는 근거가 있는데도 못 쓰는 구조라면 P0다.
