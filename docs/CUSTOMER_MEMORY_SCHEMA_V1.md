# Customer Memory Schema V1

## Purpose

이 스키마의 목적은 PDF 1회 발행이 아니라, 고객별 질문과 관심사와 watchlist를 누적해 다음 산출물의 판단 품질을 높이는 것이다.

V1 원칙은 세 가지다.

1. 현재 상품 단계에 바로 쓰이는 최소 구조만 둔다.
2. 고객 맞춤형 advisory를 가능하게 하되 과한 범용화는 하지 않는다.
3. 투자자문/민감정보로 이어질 수 있는 데이터는 저장하지 않는다.

---

## Core Objects

### `customer_profiles`

고객의 기본 운영 프로필이다.

주요 필드:

- `external_ref`: 외부 CRM, email platform, Slack DM user id 등 연결키
- `email_hash`: 평문 이메일 대신 해시 저장
- `tier`: `free`, `paid`, `vip`, `internal`
- `persona_type`: `general`, `parent`, `operator`, `investor`, `student`, `executive`
- `preferred_language`
- `knowledge_level`
- `preferred_depth`
- `consent_marketing`
- `consent_personalization`

설계 이유:

- 같은 콘텐츠라도 고객군이 다르면 설명 깊이와 watchlist가 달라진다.
- `persona_type`은 범용 플랫폼용 추상화가 아니라, 현재 상품 언어와 템플릿을 조정하기 위한 운영 필드다.

---

### `customer_memory_events`

고객과 관련된 관찰 이벤트를 누적 저장한다.

예시:

- paid 전환 hesitation
- 이해되지 않는 용어
- 특정 회사/기술에 대한 반복 관심
- 이메일 reply / Slack DM / 상담 메모
- 컨설팅 중 드러난 제약 조건

주요 필드:

- `event_type`: `feedback`, `question`, `hesitation`, `confusion`, `click`, `reply`, `consulting_note`
- `event_key`: 세부 키
- `event_value`: 자유형 JSON payload
- `source_channel`
- `source_artifact_type`
- `source_artifact_id`
- `confidence`
- `sensitivity_level`
- `expires_at`

설계 이유:

- 고객 memory는 원문 전부를 저장하는 것이 아니라, 다음 산출물에 영향을 주는 구조화 관찰만 남겨야 한다.

---

### `customer_interest_tags`

고객 관심 주제를 가중치 기반으로 유지한다.

예시:

- `physical_ai`
- `semiconductor`
- `animation_school`
- `inventory_clearance`
- `pricing`

주요 필드:

- `tag`
- `weight`
- `source`

설계 이유:

- 다음 brief에서 어떤 섹션을 강조할지 결정하는 가장 단순한 우선순위 레이어다.

---

### `customer_preference_overrides`

고객이 수시로 바꾸는 표현 방식, 출력 길이, 현재 목표, 이번 주 우선순위를 임시 레이어로 저장한다.

예시:

- “이번 주는 표보다 짧은 요약 위주”
- “당분간 입시 말고 미술 포트폴리오 중심”
- “한 달 동안은 재고 소진 전략만 보고 싶음”
- “Slack 모바일에서 3줄 결론 먼저”

주요 필드:

- `preference_key`
- `preference_value`
- `scope`: `brief`, `channel`, `campaign`, `session`
- `source`
- `confidence`
- `priority`
- `effective_from`
- `expires_at`
- `active`

설계 이유:

- `customer_profiles`는 안정적인 기본값이고, 자주 바뀌는 요구를 거기에 계속 덮어쓰면 history와 운영 의도가 같이 망가진다.
- 변덕이 큰 고객은 오히려 “기본 프로필 + 임시 override” 분리가 있어야 가볍게 대응할 수 있다.

---

### `customer_watchlists`

고객이 계속 추적해야 하는 대상 목록이다.

예시:

- 회사
- 기술
- 학교
- 입시전형
- 채널
- SKU 그룹
- 정책/규제 포인트

주요 필드:

- `entity_type`
- `entity_key`
- `priority`
- `reason`
- `active`

설계 이유:

- 고객이 돈을 내는 이유는 “새 정보” 자체보다 “내가 계속 봐야 할 대상이 정리되고 업데이트되는 것”에 가깝다.

---

### `customer_questions`

고객의 열린 질문과 답변 상태를 관리한다.

주요 필드:

- `question`
- `status`: `open`, `in_progress`, `answered`, `deferred`
- `priority`: `low`, `medium`, `high`, `urgent`
- `topic_tags`
- `last_answered_issue_id`
- `last_answered_artifact_type`
- `last_answered_artifact_id`
- `due_at`

설계 이유:

- 기존 `last_answered_issue_id`만으로는 newsletter 외의 decision brief, report, consulting note를 연결할 수 없다.
- V1에서는 기존 컬럼을 유지하면서 generic artifact reference를 추가해 하위 호환성을 지킨다.

---

### `product_upgrade_events`

고객 feedback이 실제 상품 변화로 이어졌는지 기록한다.

예시:

- scorecard 섹션 추가
- watchlist block 도입
- jargon 축소
- parent persona용 roadmap 표준화

주요 필드:

- `product_name`
- `artifact_type`
- `artifact_id`
- `source_event_ids`
- `source_feedback_ids`
- `upgrade_type`
- `description`
- `applied_to_products`

설계 이유:

- 고객 feedback이 한 번 듣고 끝난 것이 아니라, 상품 진화 자산이 되었는지를 추적해야 한다.

---

### `artifact_memory_usage`

특정 산출물이 어떤 고객 memory를 실제로 반영했는지 남기는 QA 증빙 테이블이다.

주요 필드:

- `artifact_type`
- `artifact_id`
- `customer_id`
- `audience_scope`: `individual`, `segment`, `global`
- `audience_key`
- `memory_event_ids`
- `override_ids`
- `watchlist_ids`
- `question_ids`
- `upgrade_event_ids`
- `usage_summary`
- `qa_checked`

설계 이유:

- 기존 구조는 “무슨 memory를 썼는가”는 남길 수 있지만 “누구를 위한 artifact였는가”가 빠져 있었다.
- personalization QA를 하려면 temporary override 적용 여부도 남겨야 한다.
- personalized brief를 운영하려면 최소한 `customer_id` 또는 `segment` 단위가 필요하다.

---

## Minimal Operating Rules

### Personalization Precedence

산출물 생성 시 우선순위는 아래 순서를 따른다.

1. 동의 여부와 법률/민감정보 제한
2. 만료되지 않은 최신 `customer_preference_overrides`
3. `customer_questions`의 `open/high` 항목
4. `customer_watchlists` active 항목
5. `customer_interest_tags` 상위 태그
6. `customer_profiles` 기본값

이 순서를 지키면 고객이 갑자기 주제를 바꾸더라도 전체 프로필을 재설계할 필요가 없다.

### 저장 허용

- 관심 주제
- 질문
- 혼란 포인트
- 반복적으로 추적할 대상
- 상품 개선에 도움이 되는 반응
- 상담 중 드러난 비민감 제약 조건

### 저장 금지

- 보유종목
- 매수/매도 계획
- 목표 수익률
- 자산규모
- 건강 정보
- 주민번호/주소/전화번호 등 민감 개인정보
- 동의 없는 personalization data

---

## Artifact Mapping

### `newsletter_issues`

- broad audience용 콘텐츠
- `artifact_memory_usage.audience_scope = 'segment'` 권장

### `research_reports`

- internal memo 또는 고객 맞춤형 보고서
- personalized advisory의 기본 artifact 후보

### `physical_ai_decision_brief`

현재는 `research_reports` 또는 파일 기반 산출물로 관리할 수 있다.

V1에서는 새 테이블을 추가하지 않고:

- `research_reports.report_type = 'decision_brief'`
- `artifact_memory_usage.artifact_type = 'research_report'`

조합으로 운영하는 것을 권장한다.

이유:

- 지금 단계에서 `decision_briefs` 전용 테이블을 새로 만들면 구조가 중복된다.
- first paid subscriber 이전에는 generic `research_reports`로 충분하다.

---

## Query Patterns

### 고객별 다음 brief 생성 전

1. `customer_profiles`에서 consent / 언어 / depth 확인
2. `customer_preference_overrides`의 active + non-expired 항목 조회
3. `customer_interest_tags` 상위 태그 조회
4. `customer_watchlists` active 대상 조회
5. `customer_questions` 중 `open/high` 조회
6. `customer_memory_events` 최근 hesitation/confusion/reply 조회
7. 직전 산출물의 `artifact_memory_usage` 조회

### QA 체크

다음 네 가지가 확인돼야 한다.

1. 개인화 동의 여부
2. 고객 질문 반영 여부
3. watchlist 반영 여부
4. 실제 사용 이력 `artifact_memory_usage` 기록 여부

---

## Why This Is Enough For V1

이 설계는 다음을 만족한다.

- `Physical AI`처럼 현재 도메인에 바로 적용 가능
- `부모 고객`, `재고 소진` 같은 다른 주제로 이동할 때도 스키마 재작성 없이 운영 가능
- 아직 second-system effect로 빠지지 않음
- 고객의 단기 변덕은 `customer_preference_overrides`로 흡수하고, 장기 성향은 `customer_profiles`로 유지 가능

반대로 아직 하지 않는 것:

- 별도 `decision_briefs` 테이블
- 복잡한 segment graph
- full CRM
- portfolio/financial advice memory
- 행동 예측 모델용 과도한 이벤트 로그

이건 두 번째 상품군이 실제로 매출을 만들 때 다시 판단한다.
