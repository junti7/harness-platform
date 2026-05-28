# Conference Room Handoff

Date: 2026-05-25  
Project: `harness-os`  
Target: `http://127.0.0.1:5173/` 회의실 UX 고도화

## Context
- 사용자 요구는 `회의실`을 Slack/Teams/Discord처럼 **가볍고 친숙한 메신저 UX**로 만드는 것이다.
- 과거 Slack/Notion 회의 이력은 버리고, **지금부터 생성되는 회의만 forward-only로 관리**하는 방향으로 이미 전환했다.
- `DESIGN.md` 철학상:
  - calm mission control tone
  - readable
  - not rigid admin form
  - bright, precise, operator-friendly
- 현재 가장 중요한 UX 포인트:
  1. `새 회의 시작`이 폼처럼 보이지 말 것
  2. `참여자 선택 → 바로 회의 생성` 흐름이 직관적일 것
  3. 팀별 발화 주체가 CEO에게 즉시 식별될 것
  4. 모바일에서도 카톡처럼 쓰기 쉬울 것
  5. 회의 내용은 보기 좋게 렌더링되고 지연은 매우 낮을 것

---

## What is already done

### 1. Forward-only conference room data model
기존 Slack/Notion 과거 이력 read 모델을 버리고, 앞으로 생성되는 회의만 로컬 스트림에 쌓는 구조로 바뀌었다.

Backend source of truth:
- `docs/reports/conference_room_stream.jsonl`
- `docs/reports/conference_room_notion_queue.jsonl`

관련 파일:
- `harness-os/backend/main.py`

핵심 내용:
- 회의실 읽기는 로컬 스트림 기준
- Notion은 읽기 source가 아니라 queue target
- Slack relay는 best-effort side path

### 2. Conference room API
현재 살아 있는 API:
- `GET /api/conference-room`
- `GET /api/conference-room/{item_id}`
- `POST /api/conference-room/start`
- `POST /api/conference-room/messages`

회의 시작 요청 모델:
- `ConferenceRoomStartRequest`
  - `title: str | None`
  - `agenda: str | None`
  - `participants: list[str]`

즉, **title/agenda 없이도 회의 생성 가능**하도록 backend는 이미 바뀌었다.

### 3. Auto-first-prompt
새 회의를 만들거나 비서실장에게 소집 요청하면 Jarvis가 자동 첫 질문을 남긴다.

형식:
1. 현재 판단 1문장
2. 가장 큰 리스크 1개
3. 지금 당장 필요한 추가 정보 1개

### 4. Participant status
회의 상세에서 planned participants와 실제 reply author를 비교해서:
- `소집됨`
- `입장`
상태를 보여준다.

### 5. Meeting start UX partially improved
현재 `ConferenceRoomPage.tsx`에서:
- `새 회의 시작`
- `비서실장에게 소집 요청`
버튼이 있고,
- 참여자만 골라도 생성 가능하도록 로직이 바뀌었다.

이미 반영된 UX:
- 제목/안건은 `(선택)`
- 비워두면 자동 생성/정리 안내
- `빠른 시작` 안내 문구
- `title_pending`, `agenda_pending` 시 배지/배너 표시

### 6. Message UI simplification
회의실은 현재:
- 2열 구조
  - 좌측 대화 목록
  - 중앙 대화창
- 긴 메시지 접기/펼치기
- 모바일 list/thread pane 전환
- right context panel 제거
- heavy KPI cards 제거

### 7. Team avatar system started
`ConferenceRoomPage.tsx`에 팀별 SVG glyph 기반 아바타를 추가하기 시작했다.

현재 구현 상태:
- `TeamAvatarGlyph` 함수는 이미 존재
- `Jarvis`, `KITT`, `Watchman`, `Ledger`, `Vision`, `TARS`, `Friday`, `Scribe`, `C3PO`, `Coach`, `CEO/VP` 각각 다른 glyph 제공

---

## What is incomplete right now

### 1. TeamAvatar abstraction is only partially applied
이번 세션 마지막에 아바타를 더 고급스럽게 바꾸는 작업을 시작했지만 **중간 상태**다.

현재 상태:
- `ConferenceRoomPage.tsx`에 `TeamAvatar` 컴포넌트가 새로 추가되었다.
- `import { ..., type CSSProperties } from 'react'`도 반영되었다.
- 아래 3곳에는 `TeamAvatar`가 적용되었다:
  - start panel participant buttons
  - thread list row avatar
  - message avatar

하지만 CSS는 일부만 반영되었고, 추가 shell/core 스타일은 아직 안 들어갔다.

즉, 다음 작업자는 **현재 build를 먼저 확인**하고, 아래 CSS를 마저 완성해야 한다.

### 2. App.css avatar polish patch was interrupted
아래 스타일 목표는 아직 미완료:
- avatar outer shell with subtle radial/gradient tone
- inner core ring
- chip-sized avatar variant
- participant chip button alignment

현재 존재하는 기본 스타일:
- `.conference-avatar`
- `.conference-avatar-thread`
- `.conference-avatar-message`
- `.conference-avatar svg`
- `.conference-avatar-fallback`

하지만 아래는 아직 미반영 또는 미완성:
- `.conference-avatar-shell`
- `.conference-avatar-core`
- `.conference-avatar-chip`
- chip 버튼 정렬 보강

### 3. UX still feels “stiff”
사용자 피드백:
- “아직도 UX가 이상해”
- “Teams처럼 직관적이지 않아”
- “매우 경직된 UX”

즉, 현재도 추가로 손봐야 한다.

특히 `새 회의 시작` 패널은 아직도 “모달 없는 admin form” 느낌이 남아 있다.

---

## Files to inspect first

### Backend
- `harness-os/backend/main.py`

확인 포인트:
- `ConferenceRoomStartRequest`
- `_start_conference_room`
- `_conference_room_payload`
- `_conference_room_detail`

### Frontend
- `harness-os/frontend/src/pages/ConferenceRoomPage.tsx`
- `harness-os/frontend/src/App.css`
- `harness-os/frontend/src/components/types.ts`

---

## Current expected behavior

### Meeting creation
유저는 다음처럼 회의를 시작할 수 있어야 한다:
- `새 회의 시작`
- 참여자 multi-select
- 제목/안건 비워둠 가능
- `회의 만들기`

결과:
- 회의 생성 성공
- root thread 생성
- Jarvis 자동 첫 질문 생성
- `title_pending = true`, `agenda_pending = true`일 수 있음

### After meeting ends
향후 구현 요구:
- 회의 종료 시점에 LLM이 대화 맥락을 읽어
  - 자동 제목 생성
  - 자동 안건 요약 생성
- DB/record에 저장

이건 아직 완전히 구현된 상태는 아니다. 현재는 pending flag와 placeholder UX까지만 반영된 상태로 이해하면 된다.

---

## Build / verification status

Latest known successful checks before final user turn:
- `PYTHONPYCACHEPREFIX=/private/tmp python3 -m py_compile harness-os/backend/main.py`
- `npm run build` in `harness-os/frontend`

단, 마지막 아바타 polish patch는 **중간에 끊겼기 때문에** 다시 build를 돌려 확인해야 한다.

추천 검증 순서:
1. `npm run build`
2. 필요 시 local restart
3. `회의실` 실화면 확인

---

## Highest-priority next tasks

### Priority 1. Finish avatar polish
목표:
- 이니셜/단순 glyph 수준이 아니라
- Teams/Slack처럼 “누가 말하는지 바로 읽히는” 팀별 미니 아바타
- DESIGN.md 톤 유지: 과장 금지, neon 금지, bright but precise

해야 할 일:
1. `ConferenceRoomPage.tsx`
   - `TeamAvatar`가 현재 적용된 3개 위치 외에 에러 없는지 확인
2. `App.css`
   - avatar shell/core styles 추가
   - chip avatar variant 추가
   - participant buttons 정렬 수정

추천 CSS 방향:
- soft radial highlight
- subtle border ring
- no emoji
- no cartoon excess
- no consumer-fintech gloss

### Priority 2. Make start flow feel like chat bootstrap, not form
목표:
- “회의를 생성한다”보다 “사람을 부르고 바로 대화를 시작한다”는 느낌

추천 개선:
1. 참여자 선택을 1순위 영역으로 유지
2. 제목/안건은 기본 접힘 또는 “추가 정보” 섹션으로 이동
3. CTA 문구를 더 메신저스럽게 변경
   - `회의 만들기` → `대화 열기`
   - `소집 요청 보내기` → `비서실장에게 요청`
4. 생성 직후 입력창 포커스 이동

### Priority 3. Improve conversation readability
사용자 요구:
- 텍스트가 한 폭에 안 들어오면 답답함
- markdown raw 느낌이 남으면 안 됨
- 채팅 버블은 더 산뜻해야 함

추천 작업:
1. 매우 긴 문단은 더 공격적으로 collapse
2. markdown table은 카드형 scrolling table 유지하되 visual weight를 더 낮춤
3. code-like blocks는 system log 탭에서만 강하게 보이고, 일반 회의 탭에서는 부드럽게 처리

### Priority 4. Implement end-of-meeting auto title/agenda synthesis
사용자 요구의 핵심 중 하나다.

추천 구현 방향:
1. 회의 종료 액션 정의
   - explicit “회의 종료”
   - 또는 inactivity threshold
2. 종료 시:
   - thread message aggregate
   - LLM summarizer call
   - generated `title`, `agenda_summary`
   - pending flags false
3. 결과를 stream record / DB-equivalent record에 저장

---

## Concrete next patch suggestions

### A. App.css avatar polish
Add something like:
```css
.conference-avatar-shell {
  background: radial-gradient(circle at 32% 28%, rgba(255,255,255,0.18), transparent 46%), var(--avatar-bg);
  color: var(--avatar-fg);
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,0.05),
    0 10px 22px rgba(15, 23, 42, 0.16);
}

.conference-avatar-core {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: calc(100% - 0.38rem);
  height: calc(100% - 0.38rem);
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(10px);
}

.conference-avatar-chip {
  width: 1.5rem;
  height: 1.5rem;
  margin-right: 0.42rem;
}
```

And participant button:
```css
.conference-start-participants button {
  display: inline-flex;
  align-items: center;
}
```

### B. Start flow UX copy
Possible stronger copy:
- Headline:
  - `누구와 바로 논의할까요?`
- Subcopy:
  - `참여자만 선택하면 바로 회의를 열 수 있습니다. 제목과 안건은 나중에 자동 정리됩니다.`

### C. CTA copy
Change:
- `회의 만들기` → `바로 시작`
- `소집 요청 보내기` → `비서실장 호출`

These will feel less bureaucratic.

---

## User language / terminology preferences

- `참여자` is preferred over `참석자`
- `회의실` is the product/menu name
- `AR 관제` label already renamed to `AR현황`
- `Home`, `결재`, `회의실` are standalone nav items

---

## Important warning

Do **not** reintroduce:
- old Slack history loading
- old Notion archive loading into live room
- heavy 3-column admin layout
- giant KPI cards in meeting room
- raw markdown dump look
- emoji-first avatar/icon approach

The user strongly dislikes rigid, cluttered, enterprise-form UX.

---

## Best next command sequence

```bash
sed -n '1,220p' harness-os/frontend/src/pages/ConferenceRoomPage.tsx
sed -n '660,980p' harness-os/frontend/src/App.css
npm run build
```

If backend touched:
```bash
PYTHONPYCACHEPREFIX=/private/tmp python3 -m py_compile harness-os/backend/main.py
```

If local refresh needed:
```bash
./harness-os/scripts/stop_local.sh
./harness-os/scripts/start_local.sh
```

---

## Summary for next LLM

회의실은 이미 “과거 이력 viewer”가 아니라 “앞으로의 회의용 메신저”로 방향 전환이 끝났다.  
지금 남은 핵심은:

1. 팀별 아바타를 더 완성도 있게 다듬고  
2. 시작 패널을 폼이 아니라 채팅 시작 UX처럼 바꾸고  
3. 회의 종료 후 title/agenda LLM 자동 생성까지 연결하는 것

현재 가장 immediate한 다음 작업은 **아바타 polish CSS 마무리 + start flow copy/CTA refinement**다.
