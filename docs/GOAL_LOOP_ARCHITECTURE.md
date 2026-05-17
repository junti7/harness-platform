# Goal Loop Architecture
# Version: 1.0
# Date: 2026-05-17
# Owner: Chief of Staff / Business Operations Team

---

## 1. Purpose

`/goal`은 특정 LLM의 내장 기능을 호출하는 얇은 wrapper가 아니다.

Harness의 `/goal`은 **Ralph-style closed loop**를 사업 운영에 맞게 재구성한 독자적 orchestration layer다.

핵심 원칙:

1. 목표는 대화가 아니라 **durable artifact**로 저장한다.
2. 매 루프는 **fresh context**로 시작하고, 상태는 DB/문서/metric이 이어받는다.
3. 실행 완료가 아니라 **측정 가능한 사업 성과**를 종료 조건으로 본다.
4. 대부분의 전략 수정은 팀 수준에서 자체 처리하되, **최종목표 달성 가능성이 구조적으로 낮아질 때만** CEO/VP에 escalate 한다.
5. 예측과 전략 수정의 근간은 항상 **명시적 변수와 수학적 모델**이어야 하며, 주먹구구식 판단으로 대체하지 않는다.

---

## 2. Canonical Example

예시 목표:

- "30일 내 무료 구독자 10명 확보"
- "8주 내 paid conversion 3건 확보"
- "4주 내 weekly issue production lead time 40% 단축"
- "2주 내 QA block rate를 50% 이하로 낮춤"

이 목표는 단일 task가 아니다.

필요한 것:

- channel strategy
- content cadence
- title/copy experiments
- VP readability review
- Red-Team review
- weekly metrics and forecast
- stalled / anomaly detection
- strategy revision loop

주의:

- Substack subscriber goal은 **pilot scenario**일 뿐 `/goal`의 canonical purpose가 아니다.
- `/goal`은 acquisition, conversion, retention, production speed, QA quality, cost efficiency, incident reduction 같은 서로 다른 goal type을 모두 처리할 수 있어야 한다.

---

## 3. New Team: Business Operations Team

`/goal` closed loop에서 반드시 필요한 전담 기능은 **사업운영팀 (Business Operations Team)** 이다.

역할:

- 최종목표에 대한 현재 달성 가능성 추정
- 짧은 주기의 경영 성과 관측
- 이상징후 탐지
- KPI miss가 구조적 문제인지 일시적 노이즈인지 판단
- 전략 수정안을 스스로 제안
- 상향 보고 필요 여부 판단
- 예측식, 변수 정의, 민감도, threshold를 유지/개선

사업운영팀은 Marketing, Sales, Product Planning, Subscriber Growth의 중간 coordinator가 아니라 **운영 예측 / anomaly detection / course correction owner**다.

출력:

- `goal_health_brief`
- `goal_forecast_memo`
- `strategy_revision_proposal`
- `escalation_note`

금지:

- 작은 실험 변동성만으로 CEO/VP에게 과잉 보고
- 단기 noise를 장기 실패로 과장
- 반대로 명백한 실패 징후를 방치
- 변수 정의 없이 감으로 forecast를 제시
- 수학적 근거 없는 전략 추천

---

## 4. Core Objects

`/goal` loop는 아래 객체를 중심으로 돈다.

1. `strategic_goal`
2. `goal_action_item`
3. `goal_strategy_review`
4. `goal_progress_snapshot`
5. `goal_anomaly_event`
6. `goal_forecast`
7. `goal_decision_card`
8. `goal_model_spec`
9. `goal_metric_component`
10. `goal_diagnostic_event`
11. `goal_feedback_signal`
12. `goal_revision_reason`

---

## 5. Closed Loop Stages

### Stage 1. Goal Creation

입력:

- goal title
- target metric
- target value
- deadline
- operating constraints

예:

- metric: `free_subscribers`
- target_value: `10`
- deadline: `30 days`
- channel: `owned_distribution` 또는 필요 시 특정 provider

출력:

- `strategic_goal` record
- goal brief markdown

### Stage 2. Strategy Council

참가 기본 팀:

- Chief of Staff
- Business Operations
- Product Planning
- Marketing Strategy
- Subscriber Growth
- Sales
- Vice President Content Review

필요 시:

- Legal Counsel
- QA
- Red Team

산출물:

- initial strategy memo
- team-by-team action items
- risk list
- success assumptions

### Stage 3. Action Plan Draft

각 팀은 목표 달성을 위해 담당 action item을 제안한다.

예:

- Marketing Strategy: 채널 믹스 / 주간 배포 캘린더
- Subscriber Growth: X/community post 실행안
- Product Planning: 무료/유료 경계와 conversion hook
- VP Review: jargon risk와 shareability 수정 포인트
- Business Operations: 7일/14일 forecast, anomaly trigger

### Stage 4. Red-Team Review

기본 조합:

- Claude
- Gemini
- Codex

기본 통과 기준:

- **3개 중 최소 2개 approve/clear**

단, non-negotiable finding은 자동 통과 불가.

### Stage 5. Executive Approval

CEO/VP에는 아래만 올린다.

- goal summary
- why now
- expected path to target
- top risks
- anomaly triggers
- stop / pivot trigger
- recommended action

작은 copy 수정, minor schedule tweak, low-risk channel experiment는 이 단계 없이 진행한다.
즉, executive는 **goal-level decision**을 승인하지, 매일의 미세 조정까지 승인하지 않는다.

### Stage 6. Execution

승인 후 action item이 실행된다.

실행 owner는 각 팀이지만, 진행률 / blocker / KPI는 Business Operations가 중앙 추적한다.

### Stage 7. Observation

짧은 cadence:

- daily snapshot
- 3-day signal check
- 7-day forecast review

관측 데이터:

- free subscribers
- paid subscribers
- impressions / clicks
- open / reply / share
- post volume
- conversion by channel
- production lead time
- QA block rate
- incident count
- artifact cost / unit economics

### Stage 7A. Diagnosis

관측 직후에는 반드시 **원인 진단 단계**가 따라온다.

질문:

- 노출이 부족한가
- CTR이 낮은가
- CVR이 낮은가
- 콘텐츠 품질이 낮은가
- 채널 적합도가 낮은가
- cadence가 부족한가

즉, `최종 KPI 미달`은 바로 전략 수정으로 이어지지 않고 먼저 **분해 진단**을 거친다.

### Stage 8. Local Strategy Revision

원칙:

- 대부분의 조정은 팀 수준에서 자체 수정
- CEO/VP 보고는 예외적 상황에만

예:

- 제목 포맷 수정
- CTA 문구 변경
- 채널 빈도 조정
- issue scope 축소
- community post sequencing 변경

이 단계는 Business Operations + Marketing Strategy + Product Planning이 공동 책임을 진다.

단, local revision도 반드시 아래 순서를 따른다.

1. 어떤 변수 가정이 틀렸는지 식별
2. `goal_diagnostic_event` 기록
3. `goal_model_spec` 갱신
4. 갱신된 모델 기준으로 action item 재배치

### Stage 9. Executive Escalation

다음 조건에서만 CEO/VP에 escalate 한다.

1. 현재 전략으로는 최종목표 달성 확률이 낮다고 forecast되는 경우
2. 이미 1회 이상 local revision을 했는데 성과 개선이 없는 경우
3. 목표 자체를 바꾸거나 채널/가격/메시지의 큰 방향 전환이 필요한 경우
4. brand/legal/reputation risk가 커진 경우

즉, 단순 저성과가 아니라 **전략적 방향 수정이 필요할 때만** 고위층 보고한다.

---

## 6. Forecasting and Anomaly Logic

Business Operations의 핵심은 단순 대시보드가 아니라 **예측과 이상징후 감지**다.

또한 관측 입력은 특정 플랫폼에 고정되지 않는다.

현재 구조는 아래처럼 **provider adapter**를 통해 metric을 주입할 수 있어야 한다.

- newsletter / distribution provider
- payment / conversion provider
- internal production pipeline
- QA / review system
- incident / ops system
- manual executive or operator override

현재 구현의 첫 pilot adapter는 `substack`이지만, architecture 자체는 provider-agnostic 해야 한다.

### 6.0 Mathematical Foundation Rule

모든 goal loop는 최소 하나 이상의 **명시적 수학 모형** 위에서 돌아야 한다.

허용 예:

- 선형 growth projection
- cohort conversion model
- funnel transition model
- decay / retention model
- Bayesian update
- simple scenario tree with probability bands

금지 예:

- "느낌상 잘 안 될 것 같다"
- "채널을 더 늘려보자" 같은 무모형 제안
- 변수 정의 없이 낙관/비관 판단

모든 전략 memo와 forecast memo는 최소한 아래를 포함해야 한다.

1. 변수 정의
2. 현재 추정치
3. 모델 식 또는 계산 규칙
4. 민감도 높은 변수
5. trigger threshold
6. 다음 revision 조건
7. 사용한 `goal_model_spec.version`

### 6.1 Forecast Types

- deadline forecast: 현재 속도로 목표 기한 내 달성 가능한가
- channel forecast: 어떤 채널이 실제 기여할 가능성이 높은가
- conversion forecast: 무료 → paid 전환 가능성이 생기고 있는가

### 6.2 Minimum Variable Set

예: `30일 내 무료 구독자 10명`

최소 변수:

- `S0`: 시작 시점 무료 구독자 수
- `St`: 시점 t 무료 구독자 수
- `G_t`: 기간 t 순증 구독자 수
- `I_c,t`: 채널 c의 노출 수
- `CTR_c,t`: 채널 c의 클릭률
- `CVR_c,t`: 채널 c의 구독 전환율
- `P_t`: 발행/배포 횟수
- `Q_t`: 콘텐츠 품질 score (VP/QA/engagement proxy)
- `R_t`: share/reply signal
- `D`: deadline까지 남은 일수

기본식 예:

- `ExpectedSubscribers_t = S0 + Σ_c (I_c,t * CTR_c,t * CVR_c,t)`
- `DeadlineHitProb = f(growth_rate, variance, days_remaining, channel_mix)`

### 6.2A Component Decomposition Rule

각 목표는 최종 KPI를 최소 3개 이상의 component로 분해해야 한다.

예:

- `Subscribers = Impressions * CTR * CVR`
- `Subscribers = Posts * ImpressionsPerPost * CTR * CVR`

이 component는 `goal_metric_component`로 저장된다.

진단은 항상 component variance 기준으로 시작한다.

### 6.3 Modeling Layers

권장 레이어:

1. deterministic base case
2. optimistic case
3. conservative case
4. anomaly-adjusted case

Business Operations Team은 최소한 `base / conservative / optimistic` 3개 시나리오를 유지한다.

### 6.4 Anomaly Signals

예시:

- Day 7인데 무료 구독자 증가 0~1명
- 2주 연속 open rate 하락
- post 수는 충분한데 signup conversion 거의 없음
- VP review에서 shareability가 반복적으로 낮음
- Red-Team이 같은 구조적 문제를 2회 이상 반복 지적

### 6.5 Escalation Threshold

다음은 `executive_escalation_required=true` 기본값.

- 목표 기한 내 달성 확률 < 25%
- local revision 2회 후에도 KPI 방향성 무변화
- channel thesis가 무너짐
- 가치 제안 자체가 읽히지 않음

escalation memo는 단순 KPI 미달이 아니라 반드시 아래를 포함해야 한다.

1. 어떤 component가 가장 크게 빗나갔는가
2. 그 component failure의 root cause hypothesis는 무엇인가
3. local revision으로 해결 가능한가
4. 왜 executive decision이 필요한가

### 6.6 Model Revision Rule

전략 수정은 카피만 바꾸는 것이 아니라 **모형 파라미터 갱신**을 포함해야 한다.

예:

- `CVR_x` 가정치 2.5% → 실제 0.4%면 즉시 하향 조정
- `P_t`가 부족한지, `CTR`가 낮은지, `CVR`가 낮은지 분해
- 병목 변수를 먼저 수정

즉, revision은 "전략을 새로 짠다"가 아니라:

1. 어떤 변수가 빗나갔는지 확인
2. 모델을 업데이트
3. 업데이트된 모델 기준으로 새 action item을 재배치

이다.

추가로, 각 forecast / snapshot / anomaly는 어떤 `goal_model_spec.version`을 기준으로 계산되었는지 남겨야 한다.

---

## 7. Governance Rule

`/goal`도 기존 Harness gate를 그대로 따른다.

- marketing copy 외부 발신 전: `legal_review_approve` + `red_team_clear` + `qa_clear`
- high-impact pivot: President decision 필요
- non-negotiable finding: local override 불가

---

## 8. Approval Philosophy

`/goal` 시스템은 "모든 수정은 CEO 승인" 모델이 아니다.

허용되는 local autonomy:

- minor copy change
- posting cadence tweak
- sequencing change
- CTA adjustment
- experiment re-ordering

CEO/VP 승인 필요:

- goal 변경
- KPI 기준 변경
- deadline 변경
- paid offer / pricing change
- channel strategy 대전환
- brand/legal risk 수반
- 핵심 모델 가정의 대규모 변경

---

## 9. Minimal Viable Implementation

Phase 1 MVP:

1. goal 생성
2. 전략 회의 문서화
3. action item 생성
4. Red-Team packet
5. CEO/VP goal decision card
6. daily progress snapshot
7. anomaly trigger
8. local revision memo
9. executive escalation card

---

## 10. Success Condition

`/goal` loop의 성공은 task completion이 아니라 아래다.

- 목표 달성
- 또는 조기에 실패를 감지해 손실을 줄이고 더 나은 전략으로 전환

즉, closed loop의 가치는 "자동 실행"이 아니라 **빠른 학습과 유연한 전략 수정**에 있다.

추가로, 모든 학습은 다음 질문에 답할 수 있어야 한다.

- 어떤 변수 가정이 틀렸는가
- 어떤 식이 과도하게 낙관적이었는가
- 다음 iteration에서 어떤 파라미터를 바꿨는가
