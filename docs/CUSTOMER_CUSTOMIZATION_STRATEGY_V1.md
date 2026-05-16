# Customer Customization Strategy V1

## Goal

고객 성향에 따라 매우 가볍게 산출물을 바꾸되, 고객이 수시로 변덕을 부려도 운영이 꼬이지 않게 만드는 전략이다.

핵심은 `full custom build`가 아니라 `small adaptive layers`다.

---

## Operating Principle

고객 맞춤화는 네 층으로 나눈다.

1. `stable profile`
2. `current objective`
3. `temporary override`
4. `artifact rendering`

이 네 층을 섞지 않으면, 고객이 말을 바꿔도 전체 시스템을 다시 설계할 필요가 없다.

---

## 1. Stable Profile

쉽게 안 바뀌는 정보다.

예:

- persona type
- preferred language
- knowledge level
- preferred depth
- personalization consent

저장 위치:

- `customer_profiles`

원칙:

- 상담 한 번으로 자주 안 바뀌는 값만 둔다.
- 이 레이어를 자주 덮어쓰지 않는다.

---

## 2. Current Objective

현재 고객이 해결하려는 문제다.

예:

- 이번 달은 Physical AI 투자 관찰
- 이번 분기는 애니고 진학 로드맵
- 향후 30일은 재고 5억 소진

저장 위치:

- `customer_questions`
- `customer_watchlists`
- 필요 시 `customer_memory_events`

원칙:

- “고객은 누구인가”와 “지금 무엇을 원하는가”를 분리한다.

---

## 3. Temporary Override

변덕과 순간 요구를 흡수하는 레이어다.

예:

- 오늘은 긴 보고서 말고 3줄 요약
- 당분간 차트보다 체크리스트
- 이번 주는 딸 입시보다 포트폴리오 학원 비교
- Slack에서 먼저, PDF는 나중에

저장 위치:

- `customer_preference_overrides`

운영 규칙:

- 기본 TTL은 짧게 둔다.
  - `session`: 1일
  - `brief`: 7일
  - `campaign`: 30일
- 만료되면 자동으로 기본 프로필과 watchlist 로직으로 복귀한다.
- 새 override가 이전 override와 충돌하면 최신 explicit request가 우선이다.

---

## 4. Artifact Rendering

실제 산출물은 같은 evidence를 바탕으로 가볍게만 바꾼다.

바뀌는 요소:

- 길이
- tone
- 표 vs prose 비중
- 먼저 보여줄 결론
- watchlist 강조 순서
- action block 형태
- 채널 순서 `Slack -> PDF` 또는 `PDF -> Slack`

고정해야 하는 요소:

- 근거 수준 표기
- 반론/리스크
- 금지 정보 정책
- QA / red-team

즉, customization은 rendering에서 많이 일어나고, evidence standard는 바뀌지 않아야 한다.

---

## Volatility Handling

고객이 자주 말을 바꾸는 것은 예외가 아니라 정상 상태로 본다.

대응 원칙:

1. 고객의 최신 explicit request를 override로 저장한다.
2. override에는 반드시 TTL을 둔다.
3. stable profile은 함부로 바꾸지 않는다.
4. 3회 이상 반복되는 override만 stable profile 반영 후보로 승격한다.
5. 서로 충돌하는 요구가 오면 최신 요청을 따르되, 이전 요청은 memory로 남긴다.

이렇게 해야 “이번 주만 다른 요구”와 “이제 정말 취향이 바뀐 것”을 구분할 수 있다.

---

## Segmentation Without Heavy CRM

초기에는 복잡한 CRM이 아니라 아래 정도면 충분하다.

- `parent`
- `operator`
- `executive`
- `general`

각 세그먼트마다 기본 렌더링 규칙만 둔다.

예:

- `parent`: jargon 축소, roadmap 우선, 마감 캘린더 강조
- `operator`: 실행 체크리스트, 비용/채널/리스크 강조
- `executive`: 3줄 결론, decision block, 최악의 시나리오 우선

세그먼트는 base template용일 뿐이고, 진짜 조정은 override와 watchlist에서 한다.

---

## Revenue Implication

고객이 돈을 내는 이유는 “완전히 새 보고서”가 아니라 아래 때문이다.

- 내 질문이 다음 보고서에 반영됨
- 내가 추적하는 대상이 계속 업데이트됨
- 내 이해 수준에 맞게 가볍게 조정됨
- 내가 말을 바꿔도 바로 따라옴

즉, customization의 목표는 복잡한 AI 흉내가 아니라 `빠른 반응성과 누적 신뢰`다.

---

## Implementation Order

1. `customer_profiles` 기본 운영
2. `customer_questions`와 `customer_watchlists` 활성화
3. `customer_preference_overrides` 저장/조회 추가
4. `artifact_memory_usage`에 어떤 override를 반영했는지 기록
5. 반복 override를 분석해 product upgrade 여부 판단

이 순서면 현재 코드베이스를 크게 흔들지 않고도 personalization을 붙일 수 있다.
