# EDU VP Training Day 1 LLM Switch Handoff - 2026-07-01

## Fresh Start Context

This handoff is for a `clear` / fresh-start continuation after the Day 1 LLM tool selection, coach-answer context, generic wording, and loading overlay work.

Current repo state at handoff time:

- Branch: `main`
- Latest local/origin HEAD: `cd73d0e`
- Working tree: clean
- Mac Mini edu-app production bundle verified: `assets/index-CP4FVuNa.js`
- Production edu-app URL used for verification: `http://100.97.175.44:5174/`

Codex CLI operating rule:

- Use `caveman ultra` by default unless the user explicitly disables it.
- Keep code-change summaries exact: changed files, tests, commit, push, deploy state.
- For this repo, finish user-directed production changes with verify, scoped staging, commit, push, Mac Mini deploy, and exact state report unless the user opts out.

## User Intent Captured

The user is iterating on VP Day 0 / Day 1 training UX for AI beginners.

Important product expectations:

- Day 0 should remain safety/principle oriented and should not contain meaningless extra checklist friction after the user has understood core safety concepts.
- Day 1 must continue the Day 0 structure and tone. It should not suddenly become a sparse text-only assignment screen.
- Day 1 should support multiple AI tools, not Claude-only guidance.
- AI tool terms shown to beginner users should be generic where the action is generic.
- If the user chooses a tool such as Claude, Gemini, ChatGPT, Genspark, Grok, or Perplexity, the UI should update immediately and consistently.
- Existing stale session data must not keep showing old branded copy such as `Perplexity 입력창에 붙여넣습니다.` after switching to another tool.
- While LLM/tool switching is in progress, the user must visually feel that something is changing. A clear loading overlay is expected.

## Key Files

- `harness-os/edu-app/src/components/TrainingScreen.tsx`
  - Main VP training UI.
  - Day 1 practice lab rendering.
  - LLM selection buttons.
  - Local optimistic selected-tool override.
  - AI coach answer UX, deletion UX, rating UX.

- `harness-os/edu-app/src/lib/vpTraining.ts`
  - Frontend API contract.
  - `askSafetyCoach` now sends `preferred_llm`.
  - `syncSession` sends preferred LLM changes.

- `harness-os/backend/main.py`
  - VP training state generation.
  - Day 1 install/practice lab generation.
  - Preferred LLM normalization and label mapping.
  - Safety coach request and selected-LLM answer path.

- `tests/test_edu_vp_training_flow.py`
  - Main regression suite for VP training and safety coach behavior.

- `docs/reports/completion_evidence/`
  - Completion evidence JSON files used by completion guard and pre-push checks.

## Completed Changes

### 1. Perplexity added as supported Day 1 tool

Commits:

- `578d1ef feat: add perplexity to day1 tool choices`
- `c5351b3 docs: record day1 perplexity tool deploy`

What changed:

- Backend LLM normalization supports `perplexity`.
- Display label maps to `Perplexity`.
- Day 1 install guide includes Perplexity option, app search, web fallback, and `perplexity.ai`.
- Curriculum LLM selector includes Perplexity.
- Frontend immediate guide override supports Perplexity.

Evidence:

- `docs/reports/completion_evidence/edu_training_day1_perplexity_tool_20260701.json`

### 2. Safety coach can answer "what LLM am I using?"

Commits:

- `2f6d2fd fix: answer selected llm coach questions`
- `94def98 docs: record selected llm coach answer deploy`

Problem:

- The selected LLM was stored in session state but was not sent to the safety coach answer request.
- A question like `그럼 내가 사용 중인 LLM은 뭐야?` was not guaranteed to answer from the selected tool.

Fix:

- Frontend `askSafetyCoach` request now includes `preferred_llm`.
- `TrainingScreen` passes the current selected value from local optimistic state, `ui_state`, `intake`, or customer fallback.
- Backend `EduVpTrainingSafetyCoachRequest` includes `preferred_llm`.
- Backend has deterministic path `_edu_vp_safety_coach_selected_llm_answer(...)`.
- For selected-LLM identity questions, backend answers from session value instead of model inference.
- Normal safety coach prompt now includes `[현재 선택된 AI 도구]`.

Expected answer example:

```text
현재 이 훈련에서 선택된 AI 도구는 Perplexity입니다. 다만 이것은 훈련 화면에서 고른 값이고, 실제 스마트폰이나 컴퓨터에 앱이 설치되어 있는지는 제가 직접 확인할 수 없습니다. 설치되어 있지 않으면 화면의 설치 안내나 웹 대체 경로를 따라 열면 됩니다.
```

Evidence:

- `docs/reports/completion_evidence/edu_training_selected_llm_coach_answer_20260701.json`

### 3. Branded "Claude 입력창" wording replaced with generic wording

Commits:

- `ee770f0 fix: use generic ai input wording`
- `b8c32df docs: record generic ai input wording deploy`

Problem:

- Day 1 practice table used a selected brand in a generic action, e.g. `Claude 입력창에 붙여넣습니다.`
- User requested generic beginner-friendly wording.

Backend generation now uses:

```text
선택한 AI 도구의 입력창에 붙여넣습니다.
```

Regression:

- `tests/test_edu_vp_training_flow.py` asserts the prompt-copy row uses the generic wording and does not include `Claude 입력창`.

Evidence:

- `docs/reports/completion_evidence/edu_training_day1_generic_ai_input_term_20260701.json`

### 4. Stale branded prompt-copy wording neutralized at render time

Commits:

- `d9f1ac1 fix: show tool switch overlay`
- `cd73d0e docs: record tool switch overlay deploy`

Problem:

- Even after backend generation was fixed, existing/stale session state could still contain old values like `Perplexity 입력창에 붙여넣습니다.`
- If the user switched from Perplexity to Claude, the stale practice table could keep rendering the old Perplexity wording.

Fix in `TrainingScreen.tsx`:

- Added `genericAiInputInstruction(...)`.
- Any stale value matching:

```text
ChatGPT 입력창에 붙여넣습니다.
Claude 입력창에 붙여넣습니다.
Gemini 입력창에 붙여넣습니다.
Genspark 입력창에 붙여넣습니다.
Grok 입력창에 붙여넣습니다.
Perplexity 입력창에 붙여넣습니다.
```

renders as:

```text
선택한 AI 도구의 입력창에 붙여넣습니다.
```

- The `프롬프트 복사` practice-table row is forced to generic wording regardless of old server state.

Evidence:

- `docs/reports/completion_evidence/edu_training_tool_switch_overlay_generic_prompt_20260701.json`

### 5. LLM switch loading overlay added

Commit:

- `d9f1ac1 fix: show tool switch overlay`

Behavior:

- While `toolSelecting` is non-empty, Day 1 practice lab shows an overlay.
- Overlay text:

```text
{선택 도구} 기준 안내로 변경 중
설치 안내와 실습 문구를 새 도구 기준으로 다시 맞추고 있습니다.
```

- Uses `Loader2` spinner.
- Sets `aria-busy`.
- Disables all LLM option buttons during switch to prevent overlapping requests.

Mac Mini bundle verification confirmed these strings exist in production bundle:

- `선택한 AI 도구의 입력창`
- `기준 안내로 변경 중`
- `설치 안내와 실습 문구`

## Verification Already Run

Local:

```bash
npm run build --prefix harness-os/edu-app
.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py -q
git diff --check
```

Latest relevant local results:

- edu-app build: passed
- VP training flow tests: `126 passed, 3 warnings, 64 subtests passed`
- whitespace check: passed

Mac Mini:

```bash
scripts/deploy_to_macmini.sh harness-os/edu-app/src/components/TrainingScreen.tsx docs/reports/completion_evidence/edu_training_tool_switch_overlay_generic_prompt_20260701.json
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/opt/homebrew/sbin /opt/homebrew/bin/npm run build --prefix harness-os/edu-app && uid=$(id -u) && launchctl kickstart -k gui/$uid/com.harness.edu-app'
curl -fsS http://100.97.175.44:5174/
curl -fsS http://100.97.175.44:5174/assets/index-CP4FVuNa.js | rg '선택한 AI 도구의 입력창|기준 안내로 변경 중|설치 안내와 실습 문구'
ssh macmini 'cd /Users/juntaepark/projects/harness-platform && DATABASE_URL=postgresql://localhost/harness_prod .venv/bin/python -m pytest tests/test_edu_vp_training_flow.py -q'
```

Latest Mac Mini results:

- production HTML serves `assets/index-CP4FVuNa.js` and `assets/index-CkzoPSYf.css`
- bundle content check passed
- VP training flow tests: `126 passed, 2 warnings, 64 subtests passed`

## Current Known State

At handoff time:

- `git status --short` was clean before creating this handoff file.
- Latest pre-handoff HEAD: `cd73d0e`.
- This handoff file itself still needs to be committed/pushed/deployed if the current turn does not finish that.

Expected current production behavior:

- Switching from Perplexity to Claude should not leave `Perplexity 입력창에 붙여넣습니다.` in the practice table.
- Prompt-copy row should show `선택한 AI 도구의 입력창에 붙여넣습니다.`
- During tool switch, Day 1 practice lab should show a spinner overlay.
- Once sync returns, selected install guide and tool card copy should reflect the selected tool.

## If User Reports Issue Still Persists

Check in this order:

1. Browser cache / stale bundle:

```bash
curl -fsS http://100.97.175.44:5174/ | rg -o 'assets/index-[A-Za-z0-9_-]+\\.js|assets/index-[A-Za-z0-9_-]+\\.css'
```

Expected JS at handoff: `assets/index-CP4FVuNa.js`.

2. Production bundle contains fix:

```bash
curl -fsS http://100.97.175.44:5174/assets/index-CP4FVuNa.js | rg '선택한 AI 도구의 입력창|기준 안내로 변경 중|설치 안내와 실습 문구'
```

3. Existing session state:

- Stale backend state may still hold branded `outside_app`, but `TrainingScreen.tsx` should normalize at render time.
- If the UI still shows stale brand text, inspect whether the user is viewing an older bundle or another screen/component not using `Day1PracticeLab`.

4. Tool switch sync:

- `selectDay1Tool` in `TrainingScreen.tsx` sets `localPreferredLlm(normalized)` immediately.
- It sets `toolSelecting(labelForLlm(normalized))`.
- It calls `syncSession({ preferredLlm: normalized, eventName: 'preferred_llm_changed', eventPayload: { preferred_llm: normalized } })`.
- Backend `_edu_vp_apply_preferred_llm_change(...)` rebuilds Day 1 guide and preserves user work.

## Remaining Product Concerns

The user has repeatedly flagged that Day 1 still needs to feel rich and beginner-friendly:

- Avoid long text-only screens.
- Use images, tables, concrete steps, and in-app practice scaffolding.
- If external AI app use is required, provide exact install/open/web fallback steps.
- Keep Day 1 tone consistent with Day 0.
- Avoid advanced terms like RAG in VP-facing copy.
- Use `수집된 자료` rather than `자료 확인` or `RAG 근거` in user-facing language.

## Useful Recent Commits

```text
cd73d0e docs: record tool switch overlay deploy
d9f1ac1 fix: show tool switch overlay
b8c32df docs: record generic ai input wording deploy
ee770f0 fix: use generic ai input wording
94def98 docs: record selected llm coach answer deploy
2f6d2fd fix: answer selected llm coach questions
c5351b3 docs: record day1 perplexity tool deploy
578d1ef feat: add perplexity to day1 tool choices
e177dc8 docs: record day1 immediate tool switch deploy
9e96b3e fix: make day1 tool selection immediate
f0000c2 docs: record day1 tool switch deploy verification
e4e64b0 fix: keep day1 tool switch state current
```

## Closeout Checklist For This Handoff File

If continuing from the same turn after creating this file:

```bash
git add docs/handoffs/edu_training_day1_llm_switch_handoff_20260701.md
git commit -m "docs: add day1 llm switch handoff"
git push origin main
scripts/deploy_to_macmini.sh docs/handoffs/edu_training_day1_llm_switch_handoff_20260701.md
git status --short
git rev-parse --short HEAD
git rev-parse --short origin/main
```

