# Red Team Memo — VP AI 교육 프로그램 상세 개발 계획서

> 날짜: 2026-06-20  
> 대상 문서: [docs/education/VP_AI_TRAINING_PROGRAM_DEVELOPMENT_PLAN.md](/Users/juntae.park/projects/harness-platform/docs/education/VP_AI_TRAINING_PROGRAM_DEVELOPMENT_PLAN.md)  
> 현재 라운드 owner: Codex internal red team  
> 주의: `AGENTS.md` 기준 formal cross-LLM clear는 Claude + Gemini 추가 검토가 필요하다. 본 문서는 먼저 Codex 내부 red-team 결과와 수정 반영 이력을 남긴다.

---

## 0. 최종 요약

Codex 내부 red-team 관점에서, 현재 계획서는 아래 핵심 리스크를 수정 반영한 후 **internal clear** 상태다.

수정 반영된 핵심 포인트:

1. VP를 외부 고객과 분리된 장난감 트랙으로 만들지 않고, edu case 구조를 재사용하도록 고정
2. 단순 지식 전달이 아니라 artifact-producing training으로 재설계
3. selected-LLM / device-specific guidance를 계획서에 명시
4. 외부 전이 전에 legal / QA / red-team gate를 강제
5. VP 과부하를 막기 위해 주차당 핵심 행동 수를 제한
6. `CEO 수준`을 북극성으로 두되, 6주 목표와 장기 parity 목표를 분리

다만 **formal `red_team_clear`는 아직 아님**.
이유는 이 환경에서 Claude/Gemini 독립 검토를 실제 실행할 도구가 없기 때문이다.

---

## 1. 초기 주요 우려

### Finding 1. 내부 교육이 외부 서비스와 분리된 별도 제품이 될 위험

위험:

- 내부용 따로, 외부용 따로가 되면 운영 자산이 쌓이지 않는다.

조치:

- `edu_cases` 계열 재사용 원칙 추가
- `vp_internal` track도 같은 case 구조 위에 얹도록 계획 수정

판정:

- 해소

### Finding 2. 교육이 문서 읽기 위주가 되어 실제 숙련을 만들지 못할 위험

위험:

- VP가 읽고 이해만 했다고 느끼고, 실제로는 도구 실행/검토/설명 능력이 안 생길 수 있다.

조치:

- 모든 주차에 실습과 결과물 제출을 넣음
- `edu_training_artifacts`, `edu_training_assessments`, `edu_training_friction_events` 추가

판정:

- 해소

### Finding 3. AI 초보자 대상인데도 selected-LLM / 디바이스 차이를 무시할 위험

위험:

- 실제 막힘의 대부분은 개념보다 설치/로그인/첫 실행/handoff에서 발생한다.

조치:

- selected-LLM 기준 가이드 원칙 명시
- 모바일과 PC/Mac 구간을 분리
- handoff 문구와 flow를 계획에 포함

판정:

- 해소

### Finding 4. VP에게 너무 많은 난이도와 역할을 한 번에 부여할 위험

위험:

- VP가 코딩/고급 프롬프트/교육 설계/외부 검수까지 동시에 떠안으면 실패한다.

조치:

- 비목표 명시
- 주차당 핵심 행동 1~2개 제한
- 미통과 시 다음 단계 보류 규칙 추가

판정:

- 해소

### Finding 5. 외부 재사용 단계에서 법무/표현 리스크가 되살아날 위험

위험:

- 내부 교육 자료가 그대로 외부 부모 서비스로 복제되면 금지 표현이나 과장 표현이 섞일 수 있다.

조치:

- 외부 전환 전 `red_team_clear + legal_review_approve + qa_clear` 명시
- 계획서에 대외 서비스 승인과 내부 계획을 분리

판정:

- 해소

### Finding 6. `CEO 수준` 목표를 단기 목표로 오해해 실패 기준이 비현실적으로 높아질 위험

위험:

- 목표를 높게 잡는 것은 맞지만, 6주 프로그램에서 곧바로 CEO parity를 요구하면 VP 과부하와 계획 실패로 이어질 수 있다.

조치:

- 계획서에 `궁극 목표 = CEO AI handling 수준`을 명시
- `Level 0~4 숙련 사다리`를 추가
- 6주 직접 목표는 `Level 1→2`, stretch는 `Level 3`, `Level 4`는 후속 심화 트랙으로 분리

판정:

- 해소

---

## 2. 잔여 리스크

### Residual 1. 실제 구현 없이 계획서만 좋게 끝날 위험

상태:

- medium

필요 조치:

- 바로 다음 단계에서 Day 0 intake와 artifact 저장부터 구현해야 한다.

### Residual 2. formal cross-LLM review 미완료

상태:

- medium

필요 조치:

- Claude 독립 검토
- Gemini는 2026-06-30까지 API credit 0으로 제외하고, Claude/Codex/Copilot 조합으로 대체 검토
- 충돌 시 third opinion 또는 CEO/VP escalate

### Residual 3. VP 한 사람의 패턴만 일반화해 외부 고객 전체로 과대적용할 위험

상태:

- medium

필요 조치:

- shadow user 1~2명 추가
- 디지털 트윈 simulation과 결합

---

## 3. Codex 내부 판정

- verdict: `internal_clear`
- rationale:
  - 제품 원칙과 운영 게이트가 기존 edu/VP 규약과 정합적임
  - internal-first build가 외부 서비스 자산으로 이어지도록 데이터 구조가 설계됨
  - 교과서형/허세형/디바이스 무시형 교육이 되지 않도록 가드가 문서에 반영됨

이 문서는 Codex 단독 기준으로는 다음 단계 구현을 시작할 수 있다.
다만 governance상 formal `red_team_clear` 표기는 추가 cross-LLM 검토 후에만 가능하다.

---

## 4. 실제 외부 CLI 검토 실행 기록

2026-06-20 기준 runbook에 따라 외부 CLI 실행을 시도했다.

### 4.1 Claude CLI

- `claude auth status` 확인 결과: `loggedIn=true`
- 그러나 장문/단문 review 호출은 응답 없이 장시간 hang 되었고, usable review artifact를 반환하지 못했다.

현재 해석:

- 인증 자체는 성공
- 하지만 이 환경에서 red-team review를 안정적으로 회수하는 실행 경로는 아직 불안정

판정 반영:

- `formal clear` 근거로 사용 불가

### 4.2 Gemini CLI

- smoke test 실행 결과: vendor-side `UNSUPPORTED_CLIENT`
- 에러 요지:
  - 현재 Gemini Code Assist for individuals CLI tier는 이 client에서 더 이상 지원되지 않음

현재 해석:

- 로컬 인증 문제가 아니라, 현행 CLI 자체가 사용 불가 상태

판정 반영:

- `formal clear` 근거로 사용 불가
- Gemini 대체 실행 경로(새 제품군 또는 다른 API 경로) 정비 필요

### 4.3 GitHub Copilot CLI

- smoke test 결과: `copilot_ok`
- 실제 보조 review 실행 결과: `conditional_block`

핵심 지적:

1. 범위가 너무 넓어 `VP 훈련 + 외부 부모 서비스 + internal operator mirror`를 한 번에 안고 있음
2. practice-first가 선언은 강하지만, 주차별 pass/fail 실행 계약이 약함
3. `edu_training_*`가 기존 standalone app state model과 중복될 위험이 있음
4. RAG lineage / retrieval explain contract가 더 필요함
5. operator mirror의 실제 안전 경계 정의가 부족함

판정 반영:

- Copilot 보조 검토 기준으로는 `conditional_block`

### 4.4 실행 후 종합

현재 실제 외부 실행 결과는 아래다.

- Codex 내부: `internal_clear`
- Copilot 외부 보조 검토: `conditional_block`
- Claude: 인증 성공 but review artifact 회수 실패
- Gemini: vendor blocker

따라서 2026-06-20 현재 시점에서 이 문서에 `formal red_team_clear`를 기록하면 안 된다.

현재 공식 상태는:

- `formal red team status: blocked by missing independent pair execution`
- `working status: internal_clear with external concerns`

### 4.5 Copilot conditional_block 후속 수정 반영

Copilot이 요구한 주요 수정은 계획서에 반영했다.

반영된 항목:

1. `초기 범위 제한`
   - Day 0 + Day 1 + 사용할 AI path 1개 + handoff path 1개로 축소
2. `Track 분리`
   - Track A: beginner practice
   - Track B: internal operator
3. `practice-first 계약`
   - required_action / proof_artifact / pass_fail_rubric / blocked_at_step
4. `canonical state model`
   - case/device/readiness는 기존 standalone app primitives를 owner로 유지
5. `RAG lineage 계약`
   - evidence bundle / retrieval mode / safe flag / fallback flag 명시
6. `operator mirror spec`
   - mirrored surface / data class / allowed / banned / reset path 명문화
7. `support matrix 확장 조건`
   - primary path 안정화 전에는 추가 LLM/device 확장 금지

해석:

- 문서상 구조적 약점은 상당 부분 보강됨
- 다만 이 수정 반영 후에도 `formal red_team_clear`는 다시 독립 pair 검토가 필요함
