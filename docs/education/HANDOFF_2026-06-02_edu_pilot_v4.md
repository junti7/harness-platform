# EDU Pilot Handoff — 2026-06-02 v4

## Scope

이 문서는 `부모 AI 자가점검` 독립형 PoC의 현재 구현 상태와, 다음 LLM/엔지니어가 바로 이어받아 작업할 수 있도록 남긴 hand-off다.

대상 영역:

- 독립형 앱
- Harness OS 내부 CEO/VP 테스트 런처
- 매직 링크 / 케이스 저장 / 재방문 복구
- 무료 우선 UX
- 교육 데이터 수집 확장

---

## Current URLs

- 독립형 앱:
  - `http://100.97.175.44:8000/edu-pilot-app.html`
- 브랜드 진입:
  - `http://100.97.175.44:8000/parents-first.html`
- 내부 테스트:
  - Harness OS 로그인 후 `교육 > 부모 AI 자가점검 (1호 파일럿)`

---

## What Changed In This Iteration

### 1. Resume surprise fixed

이전 문제:

- 같은 이메일이면 자동으로 마지막 케이스를 열었음
- 매직 링크도 특정 케이스가 아니라 `해당 이메일의 최신 케이스`를 다시 찾았음
- 그래서 테스트 링크를 열었을 때 예전 대화가 그대로 붙어 나와 사용자가 당황했음

현재 상태:

- `새로 시작`과 `이어서 보기`를 분리함
- `force_new`를 도입해서 같은 이메일이어도 새 케이스 생성 가능
- 매직 링크가 이제 `case_id`를 직접 저장하고, consume 시 그 케이스를 그대로 연다

검증:

- 같은 이메일
  - `force_new=false` -> 기존 `case_id=8`
  - `force_new=true` -> 새 `case_id=9`
- 매직 링크 발급/소비
  - 발급 `case_id=10`
  - 소비 후 열린 케이스도 `case_id=10`

### 2. Internal tester defaults to fresh start

CEO/VP용 내부 테스트 런처에:

- `새 케이스로 시작` 체크박스 추가
- 기본값 `ON`

즉 내부 테스트 링크 생성은 기본적으로 예전 대화를 이어붙이지 않는다.

### 3. Standalone start screen now makes intent explicit

독립형 앱 시작 화면에서 다음 네 버튼으로 분기:

- `부모 · 새로 시작`
- `부모 · 이어서 보기`
- `직장인 · 새로 시작`
- `직장인 · 이어서 보기`

---

## Files Changed

### Backend

- [harness-os/backend/main.py](/Users/juntae.park/projects/harness-platform/harness-os/backend/main.py)

핵심 변경:

- `EduPublicBootstrapRequest.force_new`
- `EduMagicLinkRequest.force_new`
- `_edu_bootstrap_customer_case()`
- `_edu_issue_magic_link()`
- `_edu_consume_magic_link()`

### Schema

- [infra/migrations/2026-06-02_edu_case_persistence.sql](/Users/juntae.park/projects/harness-platform/infra/migrations/2026-06-02_edu_case_persistence.sql)

핵심 변경:

- `edu_magic_links.case_id` 추가

### Frontend public app

- [harness-os/frontend/public/edu-pilot-app.html](/Users/juntae.park/projects/harness-platform/harness-os/frontend/public/edu-pilot-app.html)

핵심 변경:

- 시작 화면에서 `새로 시작 / 이어서 보기` 분기
- `force_new`를 bootstrap payload에 전달

### Harness OS internal launcher

- [harness-os/frontend/src/pages/EduPilotPage.tsx](/Users/juntae.park/projects/harness-platform/harness-os/frontend/src/pages/EduPilotPage.tsx)

핵심 변경:

- `새 케이스로 시작` 체크박스
- 테스트 링크 생성 시 `force_new` 포함

---

## Existing Product/UX Decisions Already Applied

### Price-first removed

현재 PoC에서는 가격을 먼저 노출하지 않음.

대신:

- 무료 커리큘럼 3개
- 다음 단계에서 받게 될 도움

중심으로 show-offer 구간을 변경함.

### Gender inference removed

이메일/이름/말투로 성별 추정 금지.

기본 호칭:

- `보호자분`
- 또는 사용자 선택 호칭

저장 필드:

- `preferred_salutation`
- `locale`
- `preferred_llm`

### Preferred LLM policy

중요 결정:

- 무료 단계에서는 LLM 선택을 사용자에게 강요하지 않음
- 유료 단계 진입 후에만 선호 LLM 선택 UI를 붙일 예정

현재는 DB 필드만 준비됨:

- `edu_customers.preferred_llm`

---

## Education Data Expansion Already Added

파일:

- [configs/sources/edu_consulting.json](/Users/juntae.park/projects/harness-platform/configs/sources/edu_consulting.json)

추가된 수집 축:

- 최근 학교 교육 이슈
  - 초등 / 중등 / 고등 / 대학교
  - 생성형 AI 과제 / 표절 / 가이드라인
- 군 복무 관련 부모 관심 주제
  - 군대 AI 교육
  - 입대 준비
  - 군 복무 변화

추가된 채널:

- `EBSi`
- `KFN`

---

## Deployment Status

이번 턴 반영 사항은 Mac Mini에 배포 완료.

배포 항목:

- backend main.py
- migration sql
- frontend dist
- public `edu-pilot-app.html`
- internal `EduPilotPage.tsx`

backend 상태:

- `com.harness.harness-os-backend`
- state: `running`

---

## Known Limitations

### 1. Public standalone still uses very thin account model

현재 재방문 식별은:

- magic link token
- 또는 same email

정식 고객 서비스 수준의 인증/권한 모델은 아직 아니다.

### 2. “Resume” UX is technically fixed, but still shallow

현재는:

- 새로 시작 / 이어보기는 분리됨

하지만 아직:

- 최근 케이스 목록
- 케이스 제목
- 마지막 대화 요약

같은 명시적 선택 UI는 없다.

### 3. Offer cards are still PoC placeholders

현재 버튼:

- 무료 단계 안내
- 다음 단계 안내

는 실제 콘텐츠 상세 페이지/커리큘럼 상세로 연결되지 않음.

alert placeholder 수준임.

### 4. Public app and internal test page are not fully unified

- standalone public app: 저장형
- internal Harness OS page: 여전히 일부 PoC 채팅 성격이 남아 있음

향후 하나의 공통 UX/데이터 계약으로 더 정리해야 함.

---

## Recommended Next Steps

우선순위 순.

### A. Improve resume UX

다음 구현 권장:

1. `이어서 보기` 선택 시
   - 최근 케이스 요약 1~3개 보여주기
2. `새로 시작` 선택 시
   - 기존 대화를 완전히 숨기고
   - “새 케이스가 시작됩니다”를 명시

### B. Replace placeholder offer actions

현재 offer card의 버튼을 실제로 연결:

1. 무료 커리큘럼 3개 상세 페이지
2. 단계형 상품 구조 설명
3. 다음 단계 onboarding flow

### C. Add customer case list for operators

Harness OS 내부에서 CEO/VP가 확인할 수 있게:

- 최근 고객 케이스 목록
- 이메일
- 현재 단계
- 최근 대화 시각
- 무료/유료 단계

표나 카드 형태로 추가 권장.

### D. Build paid-stage LLM preference selection

현재는 DB 필드만 있음.

유료 단계 진입 시에만:

- 기본 추천 사용
- Claude
- Gemini
- GPT
- Local

같은 선택 UI를 붙이면 됨.

### E. Build RAG knowledge layer for education

raw data를 바로 쓰지 말고 다음 구조 권장:

- approved_edu_knowledge
- trend_briefs
- parent_action_snippets
- school_issue_cards
- military_ai_parent_guidance

---

## Useful API Notes

### Public

- `POST /api/public/edu/bootstrap`
  - now supports `force_new`
- `GET /api/public/edu/resume`
- `POST /api/public/edu/diagnose`
- `GET /api/public/edu/magic-link/consume`

### Internal test

- `POST /api/edu/magic-link/test-create`
  - now supports `force_new`

---

## Minimal Repro For Current Behavior

### Fresh case

```bash
curl -sS -X POST http://100.97.175.44:8000/api/public/edu/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{
    "segment":"parent",
    "name":"박준태",
    "email":"pjt-test-resume@example.com",
    "preferred_salutation":"neutral",
    "locale":"ko-KR",
    "force_new": true
  }'
```

### Resume

```bash
curl -sS -X POST http://100.97.175.44:8000/api/public/edu/bootstrap \
  -H 'Content-Type: application/json' \
  -d '{
    "segment":"parent",
    "name":"박준태",
    "email":"pjt-test-resume@example.com",
    "preferred_salutation":"neutral",
    "locale":"ko-KR",
    "force_new": false
  }'
```

---

## Bottom Line

현재 상태는:

- `같은 이메일 = 무조건 이어보기`

가 아니고,

- `같은 이메일이어도 새로 시작 가능`
- `매직 링크는 발급 시점의 특정 케이스를 정확히 연다`

로 정리된 상태다.

이 hand-off 이후 작업은 `resume UX 명확화`와 `실제 무료 커리큘럼 연결`이 가장 효율적이다.
