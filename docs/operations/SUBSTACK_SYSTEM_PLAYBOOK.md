# Substack System Playbook
# Version: 1.0
# Date: 2026-05-17

---

## 1. Purpose

이 문서는 Harness가 Substack를 단순 발행 툴이 아니라 **growth system**으로 최대한 활용하기 위한 운영 규칙을 정의한다.

Phase 1 기본 전제:

- `Physical AI Weekly`의 primary publication system은 Substack으로 둔다.
- Substack의 native network를 활용해 free subscriber를 늘리고, paid conversion 전의 activation과 retention을 강화한다.
- 모든 전략은 `goal_model_spec` 변수와 KPI로 추적한다.

---

## 2. Core Principle

Substack는 아래 4개를 동시에 제공한다.

1. 발행 surface
2. 구독 capture surface
3. 네트워크 discovery surface
4. subscriber behavior surface

즉, Harness는 Substack를 다음 loop로 사용한다.

`Welcome page -> subscribe -> welcome email -> weekly issue -> Notes -> recommendations -> subscriber dashboard -> local revision`

---

## 3. Feature Map

### 3.1 Welcome Page

역할:

- 첫 방문자의 free subscribe 전환
- 포지셔닝 명확화
- 추천 blurbs를 통한 social proof

운영 규칙:

- cover image, one-line description, CTA를 weekly issue 가치에 맞게 고정
- "무엇을 다루는지"보다 "왜 지금 읽어야 하는지"를 짧게 명시
- skip button 문구도 passive하지 않게 조정
- recommendation blurbs 3개를 확보하면 즉시 노출

Primary KPI:

- visitor -> free subscriber conversion

### 3.2 Welcome Email

역할:

- free subscriber activation
- 첫 issue consumption 유도
- paid value expectation 세팅

운영 규칙:

- free subscriber welcome email은 반드시 커스텀
- 첫 3개 읽을 글, 어떤 독자를 위한 publication인지, 어떤 cadence인지 명시
- paid pitch를 강하게 넣지 말고 "왜 계속 읽어야 하는지"를 먼저 전달

Primary KPI:

- new subscriber activation
- first-week open rate

### 3.3 Notes

역할:

- Substack network 내 discovery
- follower growth
- post launch 전후 lightweight distribution

운영 규칙:

- weekly issue 외에 주 3~5회 Notes 운영
- Note 유형을 3종으로 고정
  - breaking signal reaction
  - weekly issue teaser
  - contrarian / counterpoint
- 긴 요약보다 "한 줄 해석 + 링크/restack 유도"가 우선

Primary KPI:

- follower growth
- Notes-origin subscriber growth
- weekly post click-through

### 3.4 Recommendations

역할:

- creator-to-creator growth
- recommendation digest 노출
- Welcome page endorsement 확보

운영 규칙:

- 인접 publication 5~10개를 선별해 recommendation 설정
- reciprocal recommendation 가능성이 높은 publication 우선
- 추천은 무작정 많이 하지 말고 reader fit 기준으로만 설정
- endorsement를 받으면 Welcome page에 즉시 반영

Primary KPI:

- recommendation-driven subscribers
- reciprocal recommendation count

### 3.5 Subscriber Dashboard

역할:

- free/paid/follower growth 추적
- source 분석
- active/inactive cohort 파악

운영 규칙:

- Business Operations Team이 주 1회 subscriber source를 검토
- free subscriber source가 `Substack app`, `Google`, `direct`, `recommendation` 중 어디서 오는지 기록
- goal snapshot에는 최소한 free subscribers, paid subscribers, follower count, source mix를 반영

Primary KPI:

- free subscribers
- paid subscribers
- followers
- source mix

### 3.6 Chat

역할:

- subscriber relationship 강화
- paid/community retention
- qualitative pain point 수집

운영 규칙:

- Day 1 필수 아님
- free subscriber가 적을 때는 잡음만 늘 수 있으므로, 아래 중 하나 충족 시 활성화
  - free subscribers 50+
  - paid subscriber 1+
- 처음에는 creator-led thread만 허용
- open forum은 moderation capacity 생긴 뒤 검토

Primary KPI:

- reply rate
- retained paid subscriber
- qualitative signal volume

### 3.7 Sections

역할:

- content segmentation
- email fatigue 제어
- free vs paid content lane 분리

운영 규칙:

- Phase 1 초기에는 section 남발 금지
- 최소 cadence가 안정화되기 전까지는 main weekly 하나로 운영
- 이후 필요하면 `Weekly`, `Paid Note`, `Quick Signal` 정도로 분리 검토

Primary KPI:

- section opt-in rate
- unsubscribe rate

### 3.8 Team / Contributors

역할:

- publication workflow 분리
- admin / contributor 권한 명확화

운영 규칙:

- 대표/비서실장/운영 담당 권한을 분리
- contributor에게는 글 작성/수정 권한만, growth/revenue dashboard 권한은 최소화

---

## 4. Phase 1 Execution Order

### Week 1

1. Welcome page 완성
2. free welcome email 커스텀
3. 첫 issue 발행
4. issue 발행 전후 Notes 2~3개 배포

### Week 2

1. Notes cadence를 주 3~5회로 고정
2. 인접 publication recommendation 5개 설정
3. subscriber source 첫 분석

### Week 3

1. reciprocal recommendation 시도
2. Welcome page endorsement 반영
3. Notes 유형별 CTR 차이 기록

### Week 4

1. source mix review
2. follower -> subscriber conversion gap 점검
3. Chat 활성화 조건 충족 여부 판단

---

## 5. Mathematical Model Mapping

Substack 운영 변수는 최소 아래처럼 잡는다.

- `V_w`: welcome page visitor
- `CVR_w`: welcome page -> free subscriber conversion
- `F`: follower count
- `N_p`: note publish count
- `S_r`: recommendation-driven subscriber count
- `S_d`: direct / external subscriber count
- `S_t`: total free subscribers at time t
- `P_t`: paid subscribers at time t
- `A_7`: first 7-day activation rate
- `O_1`: first issue open rate

기본식 예:

`S_t = S_(t-1) + (V_w * CVR_w) + S_r + S_d`

activation 식 예:

`A_7 = activated_new_subscribers / total_new_subscribers`

paid readiness proxy 예:

`PaidReadiness = f(O_1, reply_rate, share_rate, paid_click_rate)`

---

## 6. Diagnosis Rules

### Case A: subscriber 증가가 느림

원인 후보:

- Welcome page conversion 약함
- Notes distribution 약함
- recommendation network 없음
- external distribution copy 약함

우선순위:

1. Welcome page copy 수정
2. Notes cadence/format 수정
3. recommendation set 조정

### Case B: subscriber는 늘지만 open이 낮음

원인 후보:

- subscriber expectation mismatch
- welcome email 약함
- 제목/lead 품질 문제

우선순위:

1. welcome email 수정
2. 제목 구조 수정
3. publish timing 실험

### Case C: free는 늘지만 paid 전환이 없음

원인 후보:

- paid offer 부재
- free와 paid의 가치 구분 약함
- audience mismatch

우선순위:

1. paid note teaser 추가
2. section 또는 paid lane 분리 검토
3. subscriber feedback / hesitation 수집

---

## 7. CEO Escalation Boundary

다음은 local revision으로 처리:

- Welcome page copy 수정
- welcome email 문구 수정
- Notes cadence 변경
- recommendation set 교체
- headline format 실험

다음은 CEO/VP 보고:

- 2주 이상 subscriber growth 정체
- paid readiness proxy가 구조적으로 낮음
- recommendation / Notes / Welcome page를 모두 손봤는데도 deadline hit probability가 계속 낮음
- paid offer 구조 자체를 바꿔야 함

---

## 8. Immediate Non-Negotiables

- Welcome page는 방치하지 않는다.
- free welcome email은 기본값으로 두지 않는다.
- Notes를 안 쓰면서 Substack 성과를 판단하지 않는다.
- recommendation network 없이 Substack native growth를 평가하지 않는다.
- follower와 subscriber를 같은 것으로 취급하지 않는다.
- Chat은 조기 활성화로 운영 복잡도를 높이지 않는다.

