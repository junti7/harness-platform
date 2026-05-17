# Goal Command Surface
# Version: 1.0
# Date: 2026-05-17
# Owner: OpenClaw / Chief of Staff

---

## 1. Purpose

이 문서는 Ralph-style `/goal` closed loop를 OpenClaw command surface로 어떻게 노출할지 정의한다.

목표:

- durable goal artifact 생성
- 전략 회의와 action item orchestration
- Red-Team / executive approval 연결
- progress / forecast / anomaly / revision / escalation loop 수행
- 모든 forecast / revision을 수학 모형 기반으로 유지

---

## 2. Core Principle

`/goal`은 단일 command가 아니라 **stateful operating loop**다.

즉:

- goal 생성
- 전략 수립
- 실행
- 관측
- local revision
- executive escalation

을 반복한다.

추가 원칙:

- `/goal` loop의 모든 예측은 명시적 변수와 식을 가진 `goal_model_spec`에 의존한다.
- Business Operations Team은 모델 없는 전략 제안을 승인하지 않는다.

---

## 3. Command Set

### 3.1 Goal Create

예:

```text
/goal create "30일 내 무료 구독자 10명 확보"
```

내부 동작:

1. `strategic_goal` 생성
2. goal brief markdown 생성
3. initial strategy council packet 생성

### 3.2 Goal Plan

예:

```text
/goal plan 3
```

내부 동작:

1. Business Operations forecast 초안
2. `goal_model_spec` 초안 생성 또는 갱신
2. Marketing / Product / Subscriber Growth / Sales / VP input packet 생성
3. Chief of Staff가 action item 통합안 작성

### 3.3 Goal Red-Team

예:

```text
/goal red-team 3
```

기본 모델:

- Claude
- Gemini
- Codex

판정:

- `2-of-3 approve/clear -> pass`
- non-negotiable finding -> fix or President confirm

### 3.4 Goal Push Approval

예:

```text
/goal push-approval 3
```

내부 동작:

- CEO/VP용 goal decision card 생성
- `#exec-president-decisions` 또는 `#vp-content-review`로 전달

### 3.5 Goal Start

예:

```text
/goal start 3
```

전제:

- strategy review 존재
- red-team pass
- executive approval 존재

### 3.6 Goal Snapshot

예:

```text
/goal snapshot 3
```

내부 동작:

- KPI 수집
- `goal_progress_snapshot` 기록
- forecast 갱신
- anomaly check
- 모델 파라미터 갱신

### 3.7 Goal Revise

예:

```text
/goal revise 3
```

용도:

- local strategy revision 생성
- action item 우선순위 조정
- copy / cadence / sequencing 변경
- `goal_model_spec` 파라미터 재추정

### 3.7A Goal Diagnose

예:

```text
/goal diagnose 3
```

출력:

- primary failing component
- root cause hypothesis
- supporting signals
- local revision candidate
- escalation 여부

원칙:

- `revise` 전에 `diagnose`가 선행되어야 한다.
- diagnosis 없이 strategy revision을 시작하지 않는다.

### 3.7B Goal Provider Snapshot

예:

```text
/goal provider-snapshot 3 --provider substack
```

용도:

- provider adapter를 통해 metric 수집
- provider별 raw metric을 `goal_progress_snapshot`에 정규화
- `/goal`이 특정 플랫폼에 종속되지 않도록 유지

원칙:

- `substack`은 현재 첫 pilot adapter일 뿐 canonical provider가 아니다.
- 향후 payment, CRM, internal QA, production pipeline adapter도 같은 표면으로 붙일 수 있어야 한다.

### 3.8 Goal Escalate

예:

```text
/goal escalate 3
```

용도:

- CEO/VP 보고용 escalation card 생성
- 단순 low performance가 아니라 최종목표 달성 가능성 저하가 있을 때만 사용

### 3.9 Goal Status

예:

```text
/goal status 3
```

출력:

- current KPI
- deadline forecast
- active model summary
- health
- anomaly count
- latest diagnostic summary
- next recommended action

### 3.10 Goal Model

예:

```text
/goal model 3
```

출력:

- objective metric
- equation
- variable list
- current parameter estimates
- sensitivity order
- anomaly thresholds

---

## 4. State Machine

### 4.1 Goal States

- `draft`
- `planning`
- `red_team_review`
- `awaiting_executive_approval`
- `active`
- `local_revision`
- `escalated`
- `paused`
- `achieved`
- `abandoned`

### 4.2 Valid Transitions

1. `draft -> planning`
2. `planning -> red_team_review`
3. `red_team_review -> awaiting_executive_approval`
4. `awaiting_executive_approval -> active`
5. `active -> local_revision`
6. `local_revision -> active`
7. `active -> escalated`
8. `escalated -> active`
9. `active -> achieved`
10. `active -> abandoned`

---

## 5. Revision Logic

### 5.1 Local Revision First

다음은 local revision으로 처리한다.

- 제목/카피 수정
- 발행 빈도 조정
- CTA 순서 수정
- community post timing 수정
- action item 재배열

이 단계는 Business Operations + Marketing Strategy + Product Planning이 자체 처리한다.

단, local revision도 반드시 아래 순서를 따른다.

1. 어떤 변수 가정이 틀렸는지 식별
2. `goal_model_spec` 갱신
3. 갱신된 모델 기준으로 action item 재배치

### 5.2 Executive Escalation Only When Necessary

다음 조건일 때만 escalate 한다.

- forecast상 목표 달성 확률이 임계값 미만
- local revision 2회 후에도 개선 신호 없음
- 전략 방향 자체를 바꿔야 함
- 가격/채널/브랜드/법률 리스크 수반

---

## 6. Business Operations Team Rule

`/goal` loop에서 Business Operations Team은 필수다.

책임:

- daily/weekly business signal monitoring
- deadline forecast
- anomaly detection
- local revision recommendation
- escalation threshold 판단
- 수학 모형 유지 및 파라미터 업데이트

Business Operations Team은 모든 작은 흔들림을 CEO/VP에게 올리지 않는다.

원칙:

- **작은 이상징후 -> local correction**
- **구조적 실패징후 -> executive escalation**
- **모든 correction은 모델 업데이트를 동반**

---

## 7. Goal Decision Card

goal decision card는 기존 report decision card보다 상위 개념이다.

포함 항목:

- final goal
- current progress
- forecast to deadline
- anomaly summary
- current strategy
- recommended decision
- if blocked, what must change

---

## 8. Default Anomaly Triggers

예시:

- Day 7: target progress < 20%
- Day 14: growth rate flat
- 2 snapshots in a row: forecast probability declining
- 2 local revisions with no improvement
- channel contribution concentrated in 1 failing channel

각 anomaly trigger는 가능하면 식으로 표현한다.

예:

- `probability_to_hit < 0.25`
- `actual_value < 0.2 * expected_value by day 7`
- `d/dt subscribers <= 0 for 5 days`

---

## 9. Example Flow

목표:

- `30일 내 무료 구독자 10명`

흐름:

1. `/goal create`
2. `/goal plan`
3. `/goal red-team`
4. `/goal push-approval`
5. `/goal start`
6. `/goal snapshot` daily
7. anomaly 발견 시 `/goal revise`
8. 그래도 전망 악화 시 `/goal escalate`

---

## 10. Future Bridge Extensions

향후 `scripts/openclaw_codex_bridge.py`에 추가할 subcommand 후보:

- `goal-create`
- `goal-plan`
- `goal-red-team`
- `goal-push-approval`
- `goal-start`
- `goal-snapshot`
- `goal-revise`
- `goal-escalate`
- `goal-status`

이 문서는 command surface와 상태머신의 기준 문서다.
