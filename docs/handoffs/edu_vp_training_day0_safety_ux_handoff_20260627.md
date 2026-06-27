# Edu VP Training Day 0 Safety UX Handoff — 2026-06-27

## Codex CLI Communication Rule

사용자가 Codex CLI에서 이 작업을 이어가면 기본 응답은 **caveman full**로 한다.

- 짧게 답한다.
- 코드 변경 요약은 정확하게 한다.
- 검증 결과, 커밋, 배포 여부는 빠뜨리지 않는다.
- 불확실한 내용은 단정하지 않는다.

## Current State

배포 URL:

- `http://100.97.175.44:5174/`
- Tailscale 네트워크에서 접근 가능.

현재 로컬 작업트리:

- clean

Mac Mini 작업트리:

- 기존 untracked 파일 2개 있음.
- `docs/reports/WBR-2026-06-26.md`
- `docs/reports/ibkr_tws_paper_log.jsonl`

주의:

- 최근 원격 main에는 trading 관련 커밋도 같이 들어와 있음.
- Edu 작업과 무관하면 건드리지 말 것.

## Latest Edu Commits

- `7810f3a feat: add font size accessibility setting`
- `478450a fix: widen edu app layout on desktop`
- `dea4aaa fix: migrate unstarted day one curriculum by motivation`
- `0975cbe fix: honor motivation in vp day one curriculum`
- `9ea7ef8 fix: widen training layout on foldables`
- `1ce31ab fix: separate question archive in safety cards`
- `1640821 fix: separate question archive from training cards`

## What Changed

### 1. Day 0 AI Safety Orientation

VP training Day 0 now starts with safety and LLM operating principles before practical LLM exercises.

Main intent:

- User must understand AI/LLM is not a person.
- User must understand LLM answers are generated from learned language patterns.
- User must confirm comprehension per card.
- User can ask questions per card before moving to real practice.
- AI coach answers are logged.
- Deleted Q/A remains in backend log with flags, but hidden from user UI.

Key frontend file:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`

Key backend file:

- `harness-os/backend/main.py`

### 2. AI Coach Answer Flow

User can type questions into each Day 0 safety card.

Implemented behavior:

- `Enter` submits question.
- `Shift+Enter` inserts newline.
- Duplicate same-card same-question does not regenerate answer.
- User can delete/reset an answer.
- Delete requires confirmation.
- Deleted answers do not reappear after refresh.
- Deleted questions are also excluded from in-card `내 질문 모아보기` and top-level `Day별 질문 모아보기`.

Important persisted draft fields:

- `safety_concept_feedback`
- `safety_coach_answers`
- `safety_coach_threads`
- `deferred_safety_questions`
- `deleted_safety_answer_keys`

### 3. Question Archive UX

Problem user reported:

- `내 질문 모아보기` and training cards visually blended together.

Fix:

- In-card archive now has `질문 아카이브` badge and blue-tinted container.
- A `훈련 카드` separator appears before training cards.
- Top-level archive hides training body while open, so archive and training are not mixed.

### 4. Similar Question Routing

When user asks a question that matches a later/current card, UI can route to closest card.

Changes:

- Rule-based routing improved for misuse/risk questions.
- Backend semantic route endpoint added.
- Local/Ollama-first route support exists.
- External route fallback is opt-in.
- Routed card shows more visible amber/orange notification.
- Routed card scrolls near top.

Important case:

- `LLM을 잘못 쓸 경우 어떻게 돼?`
- Should route to `잘못 쓰면 생길 수 있는 피해`, not Day 4 backlog.

### 5. RAG and Coach Answer Quality

Implemented:

- RAG can be used for coach answers only when source fit is validated.
- UI shows a very short evidence indicator per answer.
- If a coach answer does not visibly cite RAG data, this is intentional when the retrieved material is weak or mismatched.
- The user-facing badge now distinguishes:
  - `검증 자료 반영`
  - `맞는 자료 없음`
  - `자료 확인 전`
- LLM timeout/fallback behavior optimized earlier.
- Weekly similar-question reuse added conceptually in backend logic area; verify exact current behavior before extending.

Known product stance:

- If RAG fit is weak, better show `자료 없음` than attach bad evidence.
- User values trust more than forced RAG citation.
- Day 1 can still use collected evidence through `evidence_cards` when `customer_facing_safe=true`.
- Backend source path:
  - `_edu_vp_safety_coach_evidence(...)` for Day 0/Day 1 coach answers.
  - `_edu_vp_build_day1(...)` for Day 1 `evidence_cards`.

### 6. Planned Curriculum / Rough Roadmap

User objected that saying “later Day has this” without any planned curriculum is misleading.

Implemented:

- Rough Day 0-7 curriculum outline exists.
- Day 1 is detailed-ready.
- Day 2+ are rough planned.
- Detailed future content can adapt based on user questions/interests.
- Training UI now shows a `다음 훈련 상세` panel sourced from the actual backend Day 1 object.
- This panel exposes Day 1:
  - foundation concepts
  - schedule blocks
  - sample material kits
  - tutorial steps
  - collected evidence status/cards

Where to inspect Day 1 detail:

- UI: Training screen → `다음 훈련 상세` → `목록`
- Backend: `harness-os/backend/main.py` → `_edu_vp_build_day1(...)`
- API response: `GET /api/edu/vp-training/session` → `training_state.day1`
- Admin event/audit API: `GET /api/admin/edu/vp-training/event-log?case_id=<id>`

Backend field:

- `planned_curriculum_outline`

Adjustment logging:

- If a Day 0 question is saved as a future/deeper curriculum candidate, frontend sync sends `event_name=safety_advanced_question_saved`.
- Backend now writes an additional system event:
  - `event_type=curriculum_adjustment`
  - `event_name=future_curriculum_adjustment_candidate_recorded`
- CEO/admin can inspect this through:
  - `GET /api/admin/edu/vp-training/event-log?event_type=curriculum_adjustment`
- This is the required audit trail for background tuning before later curriculum is finalized.

### 7. Motivation-Based Day 1 Curriculum

Problem:

- User selected `학습 동기=업무`, but Day 1 showed `가정통신문과 학원 일정`.
- Root cause: Day 1 builder hardcoded parent/home-school curriculum and frontend did not send explicit `motivation`.

Fix:

- Frontend now sends `motivation`.
- Backend uses explicit `motivation` first.
- Day 1 title/body/materials/RAG query branch by:
  - `work`
  - `child_study`
  - `daily`
  - `writing`
- Work mode Day 1 title:
  - `Day 1 · 업무 메모와 반복 작업을 AI로 정리해보기`
- Work mode RAG retrieval segment:
  - `worker`
- Existing unstarted legacy Day 1 sessions are migrated on refresh.
- Started/completed Day 1 is not overwritten.

Tests added:

- Work motivation keeps Day 1 and outline work-focused.
- Existing unstarted legacy Day 1 migrates to work-focused.
- Work motivation seeds dynamic curriculum path.

### 8. Responsive Layout

Problem:

- Z Fold unfolded and desktop screens were too narrow.

Implemented:

- Training, curriculum, case-select screens now use responsive width:
  - mobile: `480px`
  - foldable/tablet: `760px`
  - desktop: `960px`
  - large desktop: `1120px`

Files:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/edu-app/src/components/CurriculumScreen.tsx`
- `harness-os/edu-app/src/components/CaseSelectScreen.tsx`

### 9. Font Size Accessibility Setting

Problem:

- Font is too small for users with presbyopia, especially mid-40s+.

Implemented:

- Main screen has `글자 크기 설정`.
- User sees sample texts.
- Slider changes preview immediately.
- Presets:
  - `기본`
  - `크게`
  - `더 크게`
  - `아주 크게`
- Range:
  - `100%` to `140%`
- User must click `이 크기로 적용` to save.
- Stored in `localStorage`.
- Applies globally by setting root `font-size`.
- Letter spacing changed from `-0.01em` to `0` for readability.

Files:

- `harness-os/edu-app/src/components/FontSizeScreen.tsx`
- `harness-os/edu-app/src/lib/fontSettings.ts`
- `harness-os/edu-app/src/App.tsx`
- `harness-os/edu-app/src/components/CaseSelectScreen.tsx`
- `harness-os/edu-app/src/index.css`

Current deployed bundles after font setting:

- JS: `assets/index-DJjOe4K9.js`
- CSS: `assets/index-BIrcvthd.css`

## Commands Used For Verification

Frontend:

```bash
npm run build --prefix harness-os/edu-app
npm run lint --prefix harness-os/edu-app
```

Backend tests:

```bash
.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py tests/test_edu_curriculum_personalization.py
```

Latest backend test result during motivation work:

- `34 passed`

Deploy command:

```bash
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && git pull --ff-only && PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin npm run build --prefix harness-os/edu-app && uid=$(id -u) && launchctl kickstart -k gui/$uid/com.harness.edu-app'
```

When backend changes are included, also restart backend:

```bash
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && uid=$(id -u) && launchctl kickstart -k gui/$uid/com.harness.harness-os-backend'
```

URL check:

```bash
curl -I --max-time 8 http://100.97.175.44:5174/
curl -s --max-time 8 http://100.97.175.44:5174/ | rg -o 'assets/index-[^" ]+\.(js|css)'
```

## Files Most Likely To Edit Next

Frontend:

- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/edu-app/src/components/CaseSelectScreen.tsx`
- `harness-os/edu-app/src/components/CurriculumScreen.tsx`
- `harness-os/edu-app/src/components/FontSizeScreen.tsx`
- `harness-os/edu-app/src/lib/fontSettings.ts`
- `harness-os/edu-app/src/lib/vpTraining.ts`
- `harness-os/edu-app/src/index.css`

Backend:

- `harness-os/backend/main.py`

Tests:

- `tests/test_edu_vp_training_flow.py`
- `tests/test_edu_curriculum_personalization.py`

## Known Caveats / Watch Points

1. Existing user sessions can have stale persisted snapshots.
   - For unconfirmed Day 0, migration already exists.
   - For unstarted legacy Day 1 motivation mismatch, migration now exists.
   - For any new stale behavior, check `ui_state.stage_drafts`.

2. Deleted Q/A behavior depends on deletion flags.
   - Use `deleted_safety_answer_keys`.
   - Avoid hard-deleting logs unless explicitly requested.

3. RAG use should be conservative.
   - Bad evidence is worse than no evidence.
   - User explicitly requested validation before exposing RAG references.

4. Routing speed matters.
   - User strongly objected to long waiting.
   - If Gemini is slow, fail fast to Claude, then GPT mini, then fallback.

5. UI must suit older nontechnical users.
   - Avoid unexplained acronyms.
   - If using LLM, explain it before using it.
   - Font size and visual hierarchy matter.

6. Do not overwrite unrelated trading changes.
   - Trading commits may appear in git history.
   - Only touch edu files unless user asks trading work.

## Suggested Next Checks After Clear

1. Open `http://100.97.175.44:5174/`.
2. On main screen, click `글자 크기 설정`.
3. Confirm slider changes sample font immediately.
4. Apply `더 크게`.
5. Return to training and verify entire app font is larger.
6. On main screen with `학습 동기=업무`, create or load unstarted case.
7. Confirm Day 1 says `업무 메모와 반복 작업`, not `가정통신문과 학원 일정`.
8. In Day 0, check question archive and training cards are visually separated.
