# Edu VP Training Fresh Start Handoff — 2026-06-27

## Codex CLI Communication Rule

Codex CLI 사용 시 사용자가 별도 해제하기 전까지 **caveman full** 응답 규칙을 적용한다.

- 짧게 답한다.
- 코드 변경 요약은 정확하게 한다.
- 변경 파일, 검증 결과, 커밋, 배포 여부를 빠뜨리지 않는다.
- 사용자가 이 작업공간에서 변경 지시를 하면 마지막에 자동으로 커밋/배포까지 수행한다.
- 모든 hand-off 자료에는 "Codex CLI 사용 시 caveman full 응답 규칙을 적용하되, 코드 변경 요약은 정확하게 유지한다"는 운영 규칙을 포함한다.

## Current Deploy State

배포 URL:

- `http://100.97.175.44:5174/`
- Tailscale 네트워크에서 접근 가능.

최신 배포 확인:

- HTTP status: `200 OK`
- JS bundle: `assets/index-BgoPTemg.js`
- CSS bundle: `assets/index-ClDL7YJz.css`

최신 배포 커밋:

- `76f908b fix: render coach markdown tables`

배포 작업:

- `origin/main` push 완료.
- Mac Mini `git pull --ff-only` 완료.
- `npm run build --prefix harness-os/edu-app` 완료.
- `com.harness.edu-app` 재시작 완료.
- 마지막 변경은 frontend only라 backend 재시작은 필요하지 않았음.

## Latest Relevant Commits

- `76f908b fix: render coach markdown tables`
- `f87fe89 fix: render coach emphasis and polite guidance`
- `b3120a4 fix: classify attention mechanism questions`
- `dbf1094 fix: answer planned edu questions before guidance`
- `0434ce2 fix: persist edu training handoff state`
- `af4ca0b docs: add edu vp safety ux handoff`
- `7810f3a feat: add font size accessibility setting`
- `478450a fix: widen edu app layout on desktop`
- `dea4aaa fix: migrate unstarted day one curriculum by motivation`
- `0975cbe fix: honor motivation in vp day one curriculum`

## What Changed

### 1. Planned/Future Curriculum Questions

문제:

- Day 0에서 Day 2/3/4 등 future curriculum 주제 질문을 하면 `curriculum-backlog` 고정 답변이 먼저 나갔다.
- 질문 자체에 답하지 않고 "나중에 배운다"만 말해서 차갑고 성의 없어 보였다.

현재 동작:

- planned/future curriculum 질문도 먼저 AI 코치 경로로 보낸다.
- AI 코치 경로는 LLM + RAG validation을 사용한다.
- 맞는 자료가 있으면 `검증 자료 반영`, 없으면 `맞는 자료 없음`으로 표시한다.
- 답변 끝에만 Day 안내를 붙인다.

핵심 파일:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`

핵심 함수:

- `routePlannedCurriculumQuestion(...)`
- `plannedCurriculumGuide(...)`
- `day0BridgeAnswerForUnassignedQuestion(...)`

### 2. Attention 질문 오분류 재발 방지

문제:

- `"attention은 누가 어떻게 설정하는거야?"`가 `"Attention Is All You Need 논문 저자"` 질문으로 오분류됐다.
- `누가 + attention` 키워드만 보고 fast-template/fallback/red-team이 저자 답변으로 강제했다.

수정:

- 질문 의도 판별 함수를 backend에 추가했다.
- `attention + 어떻게/설정/정해/값/가중치/계산/작동/누가 설정`은 작동 원리 질문으로 분류한다.
- `논문/Attention Is All You Need + 저자/발표/쓴 사람`만 논문 저자 질문으로 분류한다.
- fast-template, fallback, red-team이 같은 판별 함수를 사용한다.

핵심 파일:

- `harness-os/backend/main.py`
- `tests/test_edu_vp_training_flow.py`

핵심 함수:

- `_edu_vp_question_asks_attention_mechanism(...)`
- `_edu_vp_question_asks_transformer_paper_authors(...)`
- `_edu_vp_safety_coach_fast_answer(...)`
- `_edu_vp_safety_coach_fallback(...)`
- `_edu_vp_safety_coach_red_team(...)`

테스트:

- attention 설정 질문은 fast-template 저자 답변으로 빠지지 않는다.
- attention 설정 질문은 red-team의 `missing_transformer_paper_authors`에 걸리지 않는다.
- 진짜 Transformer 논문 저자 질문은 여전히 저자 요구 검증을 받는다.

### 3. Markdown 렌더링

문제:

- `**스스로 배우는**` 같은 markdown 강조가 plain text로 보일 수 있었다.
- 표, bullet, numbered list, inline code, heading도 그대로 표시될 가능성이 있었다.

현재 지원:

- `**bold**`
- `` `inline code` ``
- `### heading`
- `- bullet`
- `1. numbered`
- markdown table

표 동작:

- markdown table이 들어오면 실제 HTML table로 렌더링한다.
- 작은 화면에서 깨지지 않게 horizontal scroll container 안에 표시한다.
- 현재 AI 코치 prompt는 짧은 본문 중심이라 표가 자주 나오지는 않는다.
- 그래도 모델이 표를 내면 이제 `| A | B |` 형태로 깨지지 않는다.

핵심 파일:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`

핵심 함수:

- `renderInlineCoachMarkdown(...)`
- `markdownTableCells(...)`
- `isMarkdownTableSeparator(...)`
- `isMarkdownTableStart(...)`
- `renderCoachTable(...)`
- `renderCoachAnswer(...)`

### 4. Polite Day Guidance

문제:

- `Day 4 · LLM 작동 원리 심화 과정에서 생성형 AI가 문장을 만드는 구조를 더 깊게 이해한다.`처럼 outline 문장이 그대로 붙어 반말처럼 보였다.

현재 동작:

- `...이해한다.`를 `...이해하게 됩니다.` 형태로 변환한다.
- Day 안내 문장은 사용자-facing 존댓말로 표시한다.

핵심 함수:

- `plannedCurriculumGuide(...)`

### 5. Check State and Position Persistence

문제:

- 브라우저 reload 또는 재입장 시 훈련 카드별 체크 상태가 사라졌다.
- 마지막으로 보던 카드 위치도 유지되지 않았다.

현재 동작:

- 체크 상태는 `stage_checked`로 저장/복원한다.
- 같은 브라우저에서는 체크 직후 localStorage에 즉시 백업한다.
- 서버 sync가 reload 전에 취소되어도 local backup으로 복원한다.
- 서버 sync가 완료된 경우 다른 기기에서도 체크가 유지된다.
- 마지막 보이던 카드 id를 `last_position.anchor_id`로 저장한다.
- 재입장 시 해당 카드로 스크롤 복원한다.

핵심 파일:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`

핵심 localStorage key:

- `vp_training_stage_draft:<caseId>:<day0|day1>`

### 6. Cross-device Training Handoff

문제:

- PC/Mac에서 훈련하다가 모바일로 이어갈 경우, PC/Mac 화면이 그대로 남아 헷갈릴 수 있었다.

현재 동작:

- 훈련 화면에 들어간 기기가 `active_training_device`를 claim한다.
- 다른 기기의 training 화면은 5초 polling으로 active device 변경을 감지한다.
- active device가 바뀌면 이전 기기는 자동으로 `내 훈련` 메인 화면으로 이동한다.
- 메인 화면에는 "다른 기기에서 이어가는 중" 안내를 표시한다.
- 이전 기기에서 다시 훈련 카드를 누르면 그 기기가 active device가 된다.

핵심 파일:

- `harness-os/backend/main.py`
- `harness-os/edu-app/src/lib/vpTraining.ts`
- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/edu-app/src/components/CaseSelectScreen.tsx`

핵심 backend fields:

- `active_training_device_id`
- `active_training_device_type`
- `active_training_case_id`
- `active_training_stage`
- `active_training_anchor_id`
- `device_claimed_at`

### 7. RAG Evidence Policy

현재 정책:

- RAG data는 지금도 coach answer와 Day 1 evidence에 연결되어 있다.
- 다만 source fit이 약하면 답변에 자료를 억지로 붙이지 않는다.
- 사용자-facing badge:
  - `검증 자료 반영`
  - `맞는 자료 없음`
  - `자료 확인 전`

핵심 backend:

- `_edu_vp_safety_coach_evidence(...)`
- `_edu_vp_validate_safety_coach_evidence(...)`
- `_edu_vp_build_day1(...)`

## Files Most Likely To Edit Next

Frontend:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/edu-app/src/components/CaseSelectScreen.tsx`
- `harness-os/edu-app/src/lib/vpTraining.ts`

Backend:

- `harness-os/backend/main.py`

Tests:

- `tests/test_edu_vp_training_flow.py`
- `tests/test_edu_curriculum_personalization.py`

Docs:

- `docs/handoffs/edu_vp_training_day0_safety_ux_handoff_20260627.md`
- `docs/handoffs/edu_vp_training_fresh_start_handoff_20260627.md`

## Verification Commands

Use these before commit/deploy:

```bash
npm run build --prefix harness-os/edu-app
npm run lint --prefix harness-os/edu-app
.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py tests/test_edu_curriculum_personalization.py
```

Latest known results:

- Frontend build: pass
- Frontend lint: pass
- Pytest: `37 passed`

## Deploy Commands

Frontend-only deploy:

```bash
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && git pull --ff-only && PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin npm run build --prefix harness-os/edu-app && uid=$(id -u) && launchctl kickstart -k gui/$uid/com.harness.edu-app'
```

Backend-included deploy:

```bash
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && git pull --ff-only && PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin npm run build --prefix harness-os/edu-app && uid=$(id -u) && launchctl kickstart -k gui/$uid/com.harness.edu-app && launchctl kickstart -k gui/$uid/com.harness.harness-os-backend'
```

Post-deploy checks:

```bash
curl -I --max-time 8 http://100.97.175.44:5174/
curl -s --max-time 8 http://100.97.175.44:5174/ | rg -o 'assets/index-[^" ]+\.(js|css)'
```

## Current Dirty Worktree

At handoff creation, these files are dirty and were intentionally not included in edu commits:

- `scripts/ibkr_tws_paper_trader.py`
- `docs/trading/TURTLE_SYSTEM_HANDOFF_2026-06-27.md`
- `tests/test_ibkr_trader_b2.py`

Treat them as unrelated trading work unless the next task explicitly asks for trading.

## Known Caveats

1. Coach answer markdown renderer is intentionally small.
   - It supports common safe markdown shapes only.
   - It does not execute or render raw HTML.

2. Tables are supported but should stay small.
   - The app renders them in horizontal scroll containers.
   - Very wide tables may be usable but not ideal on mobile.

3. Cross-device handoff uses polling.
   - Current interval: 5 seconds.
   - This is good enough for MVP.
   - SSE/WebSocket can be considered later if instant handoff is needed.

4. Local checkbox backup is browser-local.
   - It protects against immediate reload before server sync.
   - Cross-device persistence requires server sync completion.

5. Planned curriculum guidance is appended in frontend.
   - Backend answer quality still matters.
   - Do not reintroduce fixed `curriculum-backlog` answers for planned questions.

## User Preference Captured In This Run

When the user asks for code changes in this workspace:

- Implement the change.
- Verify.
- Commit relevant files.
- Push to `origin/main`.
- Deploy to Mac Mini.
- Exclude unrelated dirty files.
- Report changed files, verification, commit, deploy state.

