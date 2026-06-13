# EDU AR-044 Legal Gate Handoff

> 작성일: 2026-06-13  
> 목적: 다른 LLM/엔지니어가 `AR-044`를 실제로 닫을 수 있도록, 다음 작업 순서와 현재 설계 상태를 hand-off한다.

---

## 1. AR-044의 성격

`AR-044`는 기능 구현 AR가 아니라, **edu 공개 전 개인정보/법무 적합성 게이트**다.

즉:

- 코드가 있다고 닫으면 안 된다
- 화면 문구만 넣었다고 닫으면 안 된다
- 실제 공개 UX, 실제 데이터 모델, 실제 운영 절차, 실제 접근통제까지 맞아야 닫는다

권장 해석:

- 상위 gate: `AR-044`
- 하위 구현/문서/운영 작업: 별도 backlog/task

---

## 2. 가장 효율적인 순서

다음 1~4 순서로 진행하는 것이 바람직하다.

### 1. AR-044 운영 체크리스트 문서 작성

목적:

- `AR-044 completed`의 기준을 감이 아니라 증빙 기준으로 바꾸기

최소 포함:

- 완료 기준
- owner
- 증빙 artifact
- 확인 방법
- close 조건

### 2. 개인정보 처리방침 + 수집 고지 문구 초안 작성

공개 UX 기준으로 최소 아래를 정리해야 한다.

- 수집 항목
- 수집 목적
- 보유 기간
- 삭제/파기 기준
- 제3자 제공/위탁 여부
- 문의처
- 권리행사 방법

### 3. 현재 PoC가 실제로 받는 데이터와 문구/정책 대조

현재 설계상 관심 필드:

- age_band
- gender_identity
- current_device_type
- current_browser_context
- seeker_role
- target_person_type
- selected_llm
- email / phone

검토 포인트:

- 필수/선택 구분이 맞는가
- 과도수집인가
- 실제 공개 문구와 실제 저장 구조가 일치하는가

### 4. 접근통제 / 복구링크 정책 확정

최소 확정해야 할 것:

- `public_share` vs `private_resume` 분리
- step-up verification
- operator 접근권한
- payer vs actual participant 분리
- delete / export / read request 대응 방식

---

## 3. 현재까지 반영된 설계 문서

핵심 문서:

- [docs/education/EDU_UX_SERVICE_GUIDELINES.md](/Users/juntae.park/projects/harness-platform/docs/education/EDU_UX_SERVICE_GUIDELINES.md)
- [docs/education/EDU_STANDALONE_APP_IMPLEMENTATION.md](/Users/juntae.park/projects/harness-platform/docs/education/EDU_STANDALONE_APP_IMPLEMENTATION.md)
- [docs/education/EDU_SIMULATION_GATING.md](/Users/juntae.park/projects/harness-platform/docs/education/EDU_SIMULATION_GATING.md)

지원 문서:

- [docs/education/EDU_REALISTIC_TASK_TEMPLATES.md](/Users/juntae.park/projects/harness-platform/docs/education/EDU_REALISTIC_TASK_TEMPLATES.md)
- [docs/education/DIGITAL_TWIN_CORPUS_SPEC.md](/Users/juntae.park/projects/harness-platform/docs/education/DIGITAL_TWIN_CORPUS_SPEC.md)
- [docs/education/EDU_SEEKER_TARGET_FLOWS.md](/Users/juntae.park/projects/harness-platform/docs/education/EDU_SEEKER_TARGET_FLOWS.md)
- [docs/education/TOOL_READINESS_BLOCKAGE_TAXONOMY.md](/Users/juntae.park/projects/harness-platform/docs/education/TOOL_READINESS_BLOCKAGE_TAXONOMY.md)
- [docs/education/SIMULATION_PASS_CRITERIA.md](/Users/juntae.park/projects/harness-platform/docs/education/SIMULATION_PASS_CRITERIA.md)

이 문서들에 이미 반영된 주요 방향:

- 모바일 매직링크 첫 진입
- iPhone/Android/Windows/Mac 환경 intake
- 교과서형 과제 금지
- 고객이 선택한 LLM 기준 교육
- 설치/실행/로그인/첫 실습을 핵심 UX로 취급
- digital twin / dark factory simulation gate

---

## 4. 현재 설계상 법무/개인정보 핵심 쟁점

### A. resume link 보안

이미 red-team에서 반복 지적됨.

- public share link와 private resume link를 분리해야 함
- 새 기기에서 민감 케이스 열 때 step-up verification 필요

### B. shadow customer

- 연락처 입력 전 이탈 사용자도 생김
- pre-contact dropoff를 위해 shadow customer + merge가 필요

### C. 다중 기기 세션 충돌

- 모바일과 PC에서 같은 case를 동시에 열 수 있음
- `version_no`, `read_only`, `takeover`, lock TTL 정책이 필요

### D. target 모델과 개인정보 범위

- 자녀 1명만 전제하면 안 됨
- seeker / target / payer / actual participant의 관계가 법적으로도 중요

### E. operator 접근통제

- 누가 어떤 케이스를 볼 수 있는지
- resume link 실패/재발급/verification 실패를 누가 확인하는지

---

## 5. red-team 참고 artifact

외부 LLM 진단 결과:

- [docs/reports/llm_outputs/gemini_edu_ux_red_team_2026-06-13.md](/Users/juntae.park/projects/harness-platform/docs/reports/llm_outputs/gemini_edu_ux_red_team_2026-06-13.md)
- [docs/reports/llm_outputs/edu_ux_red_team_2026-06-13_claude.md](/Users/juntae.park/projects/harness-platform/docs/reports/llm_outputs/edu_ux_red_team_2026-06-13_claude.md)
- [docs/reports/llm_outputs/packet_edu_ux_red_team_request_2026-06-13.md](/Users/juntae.park/projects/harness-platform/docs/reports/llm_outputs/packet_edu_ux_red_team_request_2026-06-13.md)

공통적으로 지적된 것:

- 매직링크 보안
- 다중기기 충돌
- evidence-grounded twin의 선언-구현 gap
- 현실형 실습 템플릿 부족
- operator 관측성 부족
- simulation pass criteria 부재

후자는 이번 턴에서 문서로 보강됨.

---

## 6. 다른 LLM이 바로 이어서 할 일

우선순위:

1. `AR-044 운영 체크리스트` 문서 초안 작성
2. `개인정보 처리방침 / 수집 고지` 공개 UX 초안 작성
3. 현재 설계 필드와 최소수집 원칙 대조
4. resume link / step-up verification / operator access 정책 초안 작성

이 네 개가 준비되면, 그다음부터는 구현 task로 내려갈 수 있다.

---

## 7. 완료 정의

`AR-044 completed`는 아래가 다 충족될 때만 가능하다.

1. 공개 화면에 실제 고지 문구가 연결됨
2. 실제 수집 필드와 문구가 일치함
3. 보유기간/삭제/열람정정 대응 절차가 존재함
4. operator 접근통제와 resume link 정책이 실제 구현 전제와 맞음
5. 법무 관점에서 "내부 테스트 only"에서 "실고객 공개 가능"으로 상태 전환 가능함
