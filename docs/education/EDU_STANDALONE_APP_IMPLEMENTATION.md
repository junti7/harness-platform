# 부모 AI 자가점검 독립 앱 구현안

작성일: 2026-06-02  
상태: Phase 1 implementation baseline

## 1. 결정

현재 `부모 AI 진단 (1호 파일럿)`은 Harness OS 내부 탭형 PoC다.  
다음 단계는 내부 콘솔 기능이 아니라 **독립 앱**으로 전환한다.

목표:
- 외부 사용자가 링크로 바로 접속할 수 있어야 한다.
- 첫 방문에서 입력한 정보가 다음 방문에도 남아 있어야 한다.
- 채팅 기록이 아니라 **고객 케이스**가 누적되어야 한다.
- 외부 노출 문구는 법무 승인 기준에 맞춰 `자가점검 / 가이드 / 참고자료` 체계로 통일한다.

## 2. 현재 PoC 한계

1. 대화 상태가 프론트 메모리에만 있음
2. 고객별 식별자/재방문 복구 구조 없음
3. `show_offer`가 LLM 응답에 과도하게 의존
4. 구조화된 케이스 상태가 없음
5. 외부용 금지 표현(`진단`, `처방`)이 남아 있었음

## 3. 독립 앱 목표 상태

### 3.1 사용자 경험

첫 방문:
- 학부모 여부 확인
- 자녀 학년
- 가장 큰 고민 1개
- 현재 AI 사용 장면 1개
- 이메일 또는 휴대폰 입력

이후:
- 매직 링크로 재접속
- 이전 대화/요약/권장 액션 복구
- "지난번 여기까지 파악됨 → 오늘은 다음 질문 이어서" 흐름 제공

### 3.2 제품 구조

필수 화면:
1. 랜딩
2. 시작 intake
3. 대화 화면
4. 케이스 요약
5. 7일 가이드 제안
6. 재방문 이어하기

### 3.3 내부 모델

채팅 세션이 아니라 **케이스 중심**으로 저장한다.

- customer
- case
- turn
- snapshot
- offer event

## 4. 데이터 모델

### 4.1 `edu_customers`

- `id`
- `segment` (`parent` | `worker`)
- `name`
- `email`
- `phone`
- `login_channel`
- `consent_version`
- `created_at`
- `last_active_at`

### 4.2 `edu_cases`

- `id`
- `customer_id`
- `status` (`intake` | `active` | `offered` | `converted` | `archived`)
- `child_grade`
- `primary_concern`
- `ai_usage_context`
- `current_phase`
- `current_tone_level`
- `last_turn_at`
- `created_at`
- `updated_at`

### 4.3 `edu_case_turns`

- `id`
- `case_id`
- `turn_no`
- `role` (`ai` | `user`)
- `text`
- `phase`
- `tone_level`
- `quick_replies_json`
- `show_offer`
- `created_at`

### 4.4 `edu_case_snapshots`

- `id`
- `case_id`
- `summary_json`
- `detected_patterns_json`
- `recommended_next_questions_json`
- `recommended_actions_json`
- `offer_readiness_score`
- `created_at`

### 4.5 `edu_case_offers`

- `id`
- `case_id`
- `offer_type` (`guide_9900` | `parent_program_trial`)
- `shown_at`
- `accepted_at`
- `declined_at`
- `offer_context_json`

## 5. 백엔드 원칙

### 5.1 `/api/edu/diagnose` 역할 축소

현재:
- 대화 생성
- 톤 제어
- quick reply
- offer timing

변경:
- 대화 생성만 담당
- offer timing은 별도 정책 함수가 결정
- 저장은 요청 전후로 서버가 수행

### 5.2 정책 함수 분리

새 함수 예시:
- `should_show_offer(case, snapshot) -> bool`
- `extract_case_snapshot(history) -> snapshot_json`
- `next_intake_question(case) -> str | None`

LLM은 참고자이고, 전환/상태 진행은 서버 로직이 소유한다.

## 6. 프론트 원칙

### 6.1 분리 배포

권장:
- 별도 앱 엔트리 또는 별도 프론트 앱
- 예: `parents.harnessapp.ai`

### 6.2 화면 원칙

- 채팅만 보여주지 않는다
- 항상 오른쪽/하단에 `현재까지 파악된 내용`을 같이 보여준다

노출 항목:
- 자녀 학년
- 핵심 고민
- 현재 AI 사용 패턴
- 다음으로 확인할 점
- 이번 주 권장 행동

## 7. 외부 문구 규칙

외부 노출 기본어:
- `자가점검`
- `가이드`
- `참고자료`
- `사용 패턴`

금지어:
- `진단`
- `처방`
- `위험도`
- `치료`
- `전문가 판정`

## 8. 구현 순서

### Phase 1

1. 외부 노출 문구 전면 순화
2. DB 스키마 추가
3. 케이스/턴 저장 API
4. 재방문 복구 API
5. 프론트에서 case id 기반 이어하기

### Phase 2

1. snapshot 추출
2. offer policy 함수 분리
3. 매직 링크 로그인
4. PDF 가이드 생성

### Phase 3

1. 결제 연결
2. 운영자 케이스 리뷰 화면
3. 전환/재방문 분석

## 9. 즉시 실행 항목

이번 턴에서 확정:
- 외부 문구는 `자가점검/가이드` 체계로 통일
- 저장 단위는 `conversation`이 아니라 `case`
- 독립 앱으로 분리
- 재방문 이어하기를 핵심 가치로 둠

다음 구현 단위:
- 스키마 migration
- `/api/edu/cases`
- `/api/edu/cases/{id}/turns`
- `/api/edu/cases/{id}/resume`

