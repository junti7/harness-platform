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

### 8. Coach Answer Feedback Auto-Reinforcement

사용자 요구:

- AI 코치의 각 답변별로 `좋아요` / `싫어요` 피드백을 받을 수 있어야 한다.
- `좋아요`를 받은 답변은 향후에도 적극 활용할 좋은 답변 패턴으로 기록한다.
- `싫어요`를 받은 답변은 LLM이 백그라운드에서 해당 질문과 답변을 정밀 분석한다.
- 분석 결과 오류나 보완점이 있으면 `needs_improvement`로 기록하고 향후 답변 개선 rule을 남긴다.
- 오류나 보완점이 없으면 `user_mistake`로 기록한다.

현재 동작:

- 현재 답변 카드와 질문 아카이브 항목 모두 thumbs up/down 버튼을 표시한다.
- feedback 선택 상태는 `safety_coach_answer_feedback`으로 저장/복원한다.
- frontend는 `POST /api/edu/vp-training/safety-coach/feedback`을 호출한다.
- backend는 즉시 `answer_feedback_recorded` event를 남긴다.
- `좋아요`는 `actively_reuse_when_rating_up` reuse policy로 기록한다.
- `싫어요`는 FastAPI `BackgroundTasks`로 LLM review를 예약한다.
- review 결과는 `answer_auto_reinforcement_reviewed` event로 저장한다.
- LLM review 실패 시 heuristic review로 fallback한다.

핵심 파일:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/edu-app/src/lib/api.ts`
- `harness-os/edu-app/src/lib/vpTraining.ts`
- `harness-os/backend/main.py`
- `tests/test_edu_vp_training_flow.py`

핵심 backend:

- `EduVpTrainingSafetyCoachFeedbackRequest`
- `_edu_vp_safety_coach_feedback_review(...)`
- `_edu_vp_review_safety_coach_downvote_async(...)`
- `/api/edu/vp-training/safety-coach/feedback`

### 9. Empathy-First Coach Answer Policy

문제:

- 감정/고립 질문에 기존 답변이 교육 안전 규칙부터 말했다.
- `"주변에 내 얘기를 들어줄 사람이 없을 때"`라는 전제를 무시하고 `"가족이나 친구에게 이야기"` 같은 처방을 제안했다.
- `"기분이 좋은걸?"` 같은 정서 표현을 인정하지 않고 `"안전 신호가 아니다"`로 바로 교정했다.
- 이 흐름은 사용자가 사람이라는 점을 놓쳐 서비스 신뢰를 크게 떨어뜨린다.

현재 정책:

- safety coach answer version을 `2026-06-27-empathy-first-v7`로 올려 기존 냉담한 cache 재사용을 막는다.
- 감정/외로움/의존/기분 질문은 첫 문장에서 반드시 감정을 인정한다.
- AI 대화에서 위로를 느끼는 사실 자체는 부정하지 않는다.
- AI를 완전히 금지하듯 말하지 않고, 임시 위로/정리 도구로 쓸 수 있음을 인정한 뒤 경계를 설명한다.
- 사용자가 `들어줄 사람이 없다`고 말하면 그 결핍을 무시한 `가족이나 친구에게 말하세요`식 첫 처방을 금지한다.
- red-team은 감정 질문에 공감 누락, 차가운 교육 문구, 고립 맥락 무시를 품질 실패로 잡는다.
- downvote heuristic도 같은 문제를 `needs_improvement`로 기록한다.

핵심 backend:

- `_edu_vp_safety_coach_needs_empathy(...)`
- `_edu_vp_safety_coach_has_isolation_context(...)`
- `_edu_vp_safety_coach_fallback(...)`
- `_edu_vp_safety_coach_red_team(...)`

### 10. Principle Question Routing Policy

문제:

- `"왜 AI한테 질문을 하면 전기가 많이 들어?"` 같은 원리/이유 질문이 개념 정의 답변으로 빠질 수 있었다.
- frontend planned curriculum guide가 붙으면 `"Day 2에서 다룬다"`처럼 회피로 보일 수 있었다.
- 특정 질문에 하드코딩 답변을 박는 방식은 금지한다. 원칙을 route/prompt/red-team에 주입한다.

현재 정책:

- Day 0의 원리/이유 질문은 future curriculum로 먼저 넘기지 않는다.
- `왜/어떻게/원리/이유/작동/계산` 유형 질문은 오늘 이해 가능한 수준에서 직접 답한다.
- 답변 원칙: 한 줄 직접 답변 → 실제로 움직이는 것 → 쉬운 생활 비유 → 오늘 기억할 기준.
- 전기/에너지/비용/환경 질문은 하드코딩 답변 대신 prompt와 red-team 기준으로 처리한다.
- 전기/에너지 질문에 `생성형 AI 정의`만 답하면 red-team이 `answered_definition_instead_of_energy_question`으로 차단한다.
- 전기/에너지 질문에 데이터센터/서버/GPU/냉각/계산 같은 원인 설명이 부족하면 `missing_energy_use_mechanism`으로 차단한다.
- LLM 품질 실패나 timeout 뒤 fallback으로 내려가도 같은 원리 정책을 지킨다. 단락 제목이 `Transformer`여도 원리 질문이면 Transformer 정의로 답하지 않는다.
- `왜/어떻게/원리/이유/작동/계산` + AI/LLM/답변/문장/attention/Transformer/틀림/환각/확인 등 주제면 일반 원리 질문으로 본다.
- 일반 원리 질문에 단락 정의만 답하면 red-team이 `missing_principle_mechanism` 또는 `answered_definition_instead_of_principle_question`으로 차단한다.
- answer version `2026-06-27-auto-reinforcement-v10`부터 기존 cached bad answer를 재사용하지 않는다.

### 11. Downvote Auto-Reinforcement Loop

문제:

- 기존 `싫어요 → 자동강화 분석 예약됨`은 리뷰 이벤트를 저장했지만, 다음 답변 생성에 직접 주입되지 않았다.
- 같은 나쁜 답변이 cache/recent reuse로 다시 나갈 수 있었다.

현재 정책:

- downvote 즉시 `answer_feedback_recorded`를 저장한다.
- 백그라운드 리뷰가 `needs_improvement`이면 `answer_auto_reinforcement_reviewed`에 `issues`, `improvement_note`, `rejected_answer`를 남긴다.
- 다음 안전 코치 답변 생성 시 유사 질문의 `needs_improvement` 리뷰를 최근 90일 범위에서 검색한다.
- 유사도 기준을 넘은 정책은 `[자동강화 규칙]` prompt block으로 주입된다.
- 자동강화 규칙이 있으면 fast-template을 우회해 LLM이 개선 규칙을 반영하게 한다.
- red-team은 이전 downvote 답변과 유사한 새 답변을 `repeated_downvoted_answer_pattern`으로 차단한다.
- cache/recent reuse는 같은 version에서 downvote된 답변을 재사용하지 않는다.

시뮬레이션 결과:

- 가정: `"그런데 AI가 답변을 하는 작업은 왜 엄청난 전기가 든다고 해?"`에 대해 Transformer 정의 답변이 downvote되고 `needs_improvement`로 리뷰됨.
- 다음 동일/유사 질문에서 policy count `1`, prompt auto-reinforcement block `True`, improvement note injection `True`.
- 첫 모델이 같은 Transformer 정의 답변을 반복하면 red-team issues: `repeated_downvoted_answer_pattern`, `missing_energy_use_mechanism`, `missing_principle_mechanism`, `answered_definition_instead_of_principle_question`.
- 두 번째 모델 답변이 채택되고, 최종 답변은 데이터센터/서버/GPU/냉각 설명을 포함한다.

핵심 파일:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/backend/main.py`
- `tests/test_edu_vp_training_flow.py`

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
- Pytest: `44 passed`

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
