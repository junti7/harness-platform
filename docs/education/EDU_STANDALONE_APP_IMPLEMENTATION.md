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

### 1.1 디바이스 전제

이 제품의 실제 첫 진입은 대부분 `카카오톡/문자/이메일의 매직 링크를 스마트폰에서 여는 것`으로 가정한다.

따라서:

- 시작, 케이스 생성, 짧은 자가점검, 즉시 실행 과제는 모바일 기준으로 설계한다.
- 심화 실습, 긴 문서 읽기, 프롬프트 편집, 파일 다루기, 실제 AI 도구 사용은 PC/Mac 전환을 전제로 설계한다.
- 제품은 고객이 알아서 디바이스를 바꾸길 기대하지 말고 `내게 이어하기 링크 보내기`, `PC에서 이어하기`, `지금까지 요약`을 제공해야 한다.
- 실제 AI 실습 전에 `설치`, `실행`, `로그인`, `첫 화면 확인`까지를 별도 onboarding 단계로 다뤄야 한다.

상세 상위 지침은 [EDU_UX_SERVICE_GUIDELINES.md](EDU_UX_SERVICE_GUIDELINES.md)를 따른다.

## 2. 현재 PoC 한계

1. 대화 상태가 프론트 메모리에만 있음
2. 고객별 식별자/재방문 복구 구조 없음
3. `show_offer`가 LLM 응답에 과도하게 의존
4. 구조화된 케이스 상태가 없음
5. 외부용 금지 표현(`진단`, `처방`)이 남아 있었음
6. 공유 링크와 개인 복구 링크의 보안 경계가 얕음
7. 모바일에서 PC/Mac로 넘길 때 다중 세션 충돌 정책이 없음

## 3. 독립 앱 목표 상태

### 3.1 사용자 경험

첫 방문:
- 스마트폰에서 1분 안에 시작 가능
- 긴 자유서술보다 선택형 + 짧은 답변 우선
- 연락처를 아직 안 남겨도 임시 시작 가능
- seeker 연령대 선택
- seeker 성별 선택 (비공개/응답 안 함 포함)
- 현재 기기 선택
  - iPhone
  - Android
- 현재 브라우저 상태 확인
  - 카카오 인앱
  - 일반 브라우저
- 이메일 또는 휴대폰 입력
- 현재 누구 문제로 왔는지 확인
  - 본인
  - 자녀
  - 부모
  - 배우자/가족
- 가장 큰 고민 1개
- 현재 AI 사용 장면 1개

이후:
- 매직 링크로 재접속
- 이전 대화/요약/권장 액션 복구
- "지난번 여기까지 파악됨 → 오늘은 다음 질문 이어서" 흐름 제공
- 필요 시 `지금은 모바일에서 여기까지`, `다음 단계는 PC/Mac 권장`을 명시
- 고객이 본인에게 링크를 다시 보낼 수 있어야 함
- 공유용 링크와 개인 복구 링크를 명확히 구분
- 새 기기에서 열면 필요 시 소유자 재확인
- 같은 케이스가 다른 기기에서 열려 있으면 충돌 경고 또는 읽기 전용 처리
- PC/Mac 실습 전에는 `도구 준비 단계`를 따로 둔다
  - 설치 필요 여부 확인
  - 설치 링크 제공
  - 실행 성공 확인
  - 로그인 성공 확인
  - 첫 실습 시작 확인
- 큰 화면 실습 전에는 사용할 기기 환경을 다시 묻는다
  - Windows / Mac
  - 회사/학교 기기인지
  - 앱 설치 가능한지
  - 옆에서 도와줄 사람이 있는지
- 실습 전에는 사용할 LLM을 고객이 직접 선택한다
  - Claude
  - Gemini
  - ChatGPT
  - Codex / Claude Code 계열
  - 아직 모름
- 이후 가이드는 선택된 LLM 기준으로만 제공한다

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
- `is_shadow`
- `name`
- `age_band`
- `gender_identity`
- `current_device_type`
- `current_os_family`
- `current_browser_context`
- `selected_llm`
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
- `seeker_role` (`self` | `parent_of_child` | `child_of_parent` | `spouse_or_family` | `manager_or_peer`)
- `target_person_type` (`self` | `child` | `parent` | `spouse` | `family` | `team`)
- `child_grade`
- `primary_concern`
- `ai_usage_context`
- `recommended_device` (`mobile_ok` | `desktop_recommended` | `desktop_required`)
- `tool_readiness_state` (`not_needed` | `install_needed` | `install_started` | `installed_not_run` | `run_ok` | `login_ok` | `first_task_started`)
- `desktop_target_os`
- `managed_device_flag`
- `helper_available_flag`
- `selected_llm_for_training`
- `current_phase`
- `current_tone_level`
- `version_no`
- `active_device_session_id`
- `last_turn_at`
- `created_at`
- `updated_at`

### 4.2A `edu_case_targets`

- `id`
- `case_id`
- `target_type` (`self` | `child` | `parent` | `spouse` | `family` | `team`)
- `display_label`
- `grade_or_age_band`
- `relationship_note`
- `created_at`

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

### 4.6 `edu_magic_link_events`

- `id`
- `case_id`
- `customer_id`
- `link_kind` (`public_share` | `private_resume`)
- `device_type`
- `browser_family`
- `is_inapp_browser`
- `issued_at`
- `opened_at`
- `expired_at`
- `failed_reason`

### 4.7 `edu_device_sessions`

- `id`
- `case_id`
- `device_label`
- `device_type`
- `os_family`
- `browser_family`
- `is_inapp_browser`
- `last_seen_at`
- `state` (`active` | `superseded` | `read_only`)
- `lock_expires_at`
- `takeover_required_flag`

### 4.9 `edu_tool_readiness_events`

- `id`
- `case_id`
- `tool_name`
- `platform` (`android` | `ios` | `windows` | `mac`)
- `event_type` (`install_prompted` | `install_started` | `install_completed` | `app_opened` | `login_completed` | `first_task_started` | `blocked`)
- `blocked_reason`
- `environment_note`
- `llm_vendor`
- `created_at`

### 4.8 `edu_case_access_guard`

- `id`
- `case_id`
- `owner_customer_id`
- `payer_customer_id`
- `contact_verification_required`
- `last_verified_at`
- `created_at`

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
- `issue_resume_link(case, device_context) -> link`
- `verify_case_access(case, channel, device_context) -> allow/step_up_required`
- `lock_case_session(case, device_session) -> read_write/read_only`
- `next_tool_setup_step(case, tool, platform) -> action_card`
- `record_tool_readiness(case, tool, event) -> None`
- `recommend_llm(case_profile) -> ranked_options`
- `build_first_real_output_task(case, selected_llm) -> action_card`

LLM은 참고자이고, 전환/상태 진행은 서버 로직이 소유한다.

정책 함수 구현 원칙:

- `show_offer`, `quick_replies`, `snapshot`은 LLM 원시 출력이 아니라 서버 검증/정제 후 확정값을 저장한다.
- LLM은 제안자이고, 서버 정책 함수가 최종 결정자다.
- `extract_case_snapshot`은 실패 시 deterministic fallback을 가진다.
- selected LLM mismatch는 정책 단계에서 차단한다.

### 5.3 다중 기기 세션 제어 규칙

초기 기준:

- 새 기기에서 same case 오픈 시 기존 active session 감지
- 기존 세션이 최근 `90초` 안에 active면 새 기기는 기본 `read_only`
- 사용자가 명시적으로 `이 기기에서 이어하기`를 누르면 takeover 수행
- takeover 시 기존 기기는 `superseded` 상태가 되고 입력 UI 잠금
- 서버 lock TTL 기본값은 `120초`
- turn 저장 시 `version_no` 불일치면 저장 거부 + 새로고침 요구

구현 힌트:

- 상태 동기화는 polling으로 시작해도 된다
- 필요 시 추후 websocket으로 확장

## 6. 프론트 원칙

### 6.1 분리 배포

권장:
- 별도 앱 엔트리 또는 별도 프론트 앱
- 예: `parents.harnessapp.ai`

### 6.2 화면 원칙

- 채팅만 보여주지 않는다
- 항상 오른쪽/하단에 `현재까지 파악된 내용`을 같이 보여준다
- 모바일에서는 `지금 할 것`
- 데스크톱에서는 `지금 할 것 + 실습 자료 + 복사할 프롬프트`
- 모바일에서 데스크톱으로 보낼 때는 다운로드보다 `내게 링크 보내기`를 우선한다
- 복구 링크는 `개인 기록을 여는 링크`라는 점을 명시한다
- 최초 intake에서 연령/성별은 선택형 칩으로 빠르게 받는다
- 연령/성별은 사용자 명시 입력만 사용하고 추정하지 않는다
- 기기/OS/브라우저/주변 도움 가능 여부도 선택형으로 짧게 받는다
- 같은 실습이라도 iPhone, Android, Windows, Mac별 카드 문구를 다르게 제공한다
- 고객이 선택한 LLM별로 카드 문구와 설치/실행 흐름을 다르게 제공한다
- 설치가 필요한 구간에서는 `설치 카드 → 실행 카드 → 로그인 카드 → 첫 실습 카드` 순서로 한 단계씩만 보여준다
- dry 문구 대신, 막히는 지점이 반영된 guided action card를 사용한다
- 첫 실습은 `교과서형 대화 과제`보다 `고객이 원하는 방향의 실제 결과물 만들기`를 우선한다
- 첫 실습 카드의 원본은 [EDU_REALISTIC_TASK_TEMPLATES.md](EDU_REALISTIC_TASK_TEMPLATES.md)에서 가져온다

노출 항목:
- seeker 연령대 / 성별
- seeker 현재 기기 / 브라우저 상태
- 자녀 학년
- 핵심 고민
- 현재 AI 사용 패턴
- 다음으로 확인할 점
- 이번 주 권장 행동
- 이 단계 권장 기기 (`휴대폰에서 가능` / `PC/Mac 권장`)
- 현재 열려 있는 기기 상태 (`이 기기에서 계속` / `다른 기기에서 이어짐`)
- 현재 도구 준비 상태 (`설치 전` / `설치 완료` / `실행 확인` / `로그인 확인` / `실습 시작`)
- 예정된 큰 화면 환경 (`Windows` / `Mac` / `미정`)
- 선택한 LLM (`Claude` / `Gemini` / `ChatGPT` / `Codex 계열` / `미정`)

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
2. shadow customer + case 생성
3. DB 스키마 추가
4. 케이스/턴 저장 API
5. 재방문 복구 API
6. 프론트에서 case id 기반 이어하기
7. 공유 링크 vs 개인 복구 링크 분리
8. 도구 준비 상태 추적의 최소 스키마 반영
9. 선택 LLM 저장 및 분기 가이드 반영
10. `show_offer/quick_replies/snapshot` 서버 확정 로직 반영
11. 다중 기기 lock / takeover 최소 정책 반영

### Phase 2

1. snapshot 추출
2. offer policy 함수 분리
3. 매직 링크 로그인
4. 소유자 재확인(step-up verification)
5. 다중 기기 세션 제어
6. PDF 가이드 생성
7. guided tool setup cards
8. 설치/실행/로그인 blockage taxonomy
9. LLM별 첫 결과물 생성 카드
10. 교과서형 과제 제거 및 현실형 과제 템플릿 도입
11. blockage taxonomy 연동
12. seeker-target 다중 흐름 구체화

### Phase 3

1. 결제 연결
2. 운영자 케이스 리뷰 화면
3. 전환/재방문 분석
4. payer와 actual participant 분리

## 9. 즉시 실행 항목

이번 턴에서 확정:
- 외부 문구는 `자가점검/가이드` 체계로 통일
- 저장 단위는 `conversation`이 아니라 `case`
- 독립 앱으로 분리
- 재방문 이어하기를 핵심 가치로 둠
- 모바일 매직 링크를 기본 진입점으로 둠
- PC/Mac 심화 전환을 제품이 명시적으로 안내해야 함
- 공유 링크와 민감 기록 복구 링크를 분리해야 함
- 무연락처 초기 진입을 위해 shadow customer가 필요함
- 다중 기기 동시 수정 충돌을 막아야 함
- 설치/실행/로그인/첫 실습 자체를 별도 UX 단계로 관리해야 함
- 고객이 선택한 LLM 기준으로만 교육해야 함
- 부모 과제도 `아이에게 물어보라`가 아니라 `부모가 먼저 결과를 보고 눈이 뜨이는 실습` 중심이어야 함

다음 구현 단위:
- 스키마 migration
- `/api/edu/cases`
- `/api/edu/cases/{id}/turns`
- `/api/edu/cases/{id}/resume`
- `/api/edu/cases/{id}/send-link`
- `최근 케이스 목록 + 기기 전환 UX`
- `/api/edu/cases/{id}/verify-access`
- `/api/edu/cases/{id}/lock-session`
- `/api/edu/cases/{id}/tool-readiness`
- guided setup card renderer
