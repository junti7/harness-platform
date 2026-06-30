# EDU VP Training Day 1 Visual/Install Handoff - 2026-06-30

## Operating Rule

Codex CLI 사용 시 caveman full 응답 규칙을 적용하되, 코드 변경 요약은 정확하게 유지한다.

This handoff is for a fresh start after the EDU VP training Day 0/Day 1 stabilization, Day 1 curriculum depth work, smartphone wording cleanup, and Day 1 visual/install guidance deployment.

## Current Repo State

- Workspace: `/Users/juntae.park/projects/harness-platform`
- Branch: `main`
- Latest local HEAD at handoff creation: `3c89d5e`
- Latest pushed commits in this loop:
  - `7405dca fix: remove edu iphone device literals`
  - `76068df docs: complete edu iphone literal removal evidence`
  - `8965dd9 fix: normalize legacy edu mobile scene copy`
  - `12e41e6 docs: complete edu legacy scene evidence`
  - `6ec1d22 feat: add guided edu day1 practice lab`
  - `8b114ed docs: complete edu day1 practice lab evidence`
  - `7e1f9e5 feat: add edu day1 training images`
  - `3c89d5e docs: complete edu day1 image evidence`
- Known unrelated dirty file to preserve:
  - `docs/education/edu_parents_first_parent_landing.html` is deleted in the working tree and was not part of this work.

## User Requests Covered

The user reported these product issues:

- Day 0 had meaningless checklist items below "오늘의 순서"; Day 0 should be enough after checking "AI를 쓰기 전에 먼저 알아야 할 것" and asking questions.
- "질문만 먼저 저장" was redundant because autosave already preserves previous information.
- Main list showed Day 0 progress incorrectly as `0%` or `50%` even after Day 0 completion.
- Entering the training screen could show Day 1 while main card still showed partial Day 0 progress.
- Pressing Day 0 tab bounced back to Day 1 or made Day 0 hard to inspect.
- Existing Day 0 checked/questions state appeared lost and needed restoration.
- Day 1 curriculum was too thin for an 85-minute course.
- Day 1 UX tone must continue Day 0 structure and not suddenly change.
- `iPhone` wording must become neutral `스마트폰`, because Android users may be confused.
- Day 1 must not ask beginners to leave the app and "figure it out"; it should guide the practice in-app as much as possible.
- If another app is necessary, the UX must explain how to install/open Claude/Gemini/ChatGPT step by step.
- Training cards needed educational images, tables, and a less text-only UX.
- Images were still not visible because no assets/rendering existed.

## What Changed

### Day 0 / Day 1 Flow Stabilization

Core file:

- `harness-os/backend/main.py`

Key behavior:

- Day 0 safety gate is streamlined. After safety confirmation, Day 0 can complete and Day 1 can open.
- Day 0 progress/list calculation was fixed so completed Day 0 does not keep showing `0%` or `50%`.
- Tab selection and selected-stage refresh behavior were hardened so Day 0 does not bounce back to Day 1 unexpectedly.
- Existing Day 0 questions/checks are preserved through refresh and restore paths.

Evidence files:

- `docs/reports/completion_evidence/edu_day0_day1_gate_streamline_20260628.json`
- `docs/reports/completion_evidence/edu_day0_list_progress_recalc_20260628.json`
- `docs/reports/completion_evidence/edu_day0_progress_completion_20260628.json`
- `docs/reports/completion_evidence/edu_day0_safety_records_visible_restore_20260630.json`
- `docs/reports/completion_evidence/edu_training_day0_tab_bounce_fix_20260630.json`
- `docs/reports/completion_evidence/edu_training_stage_progress_tab_stability_20260629.json`

### Day 1 Curriculum Depth

Core file:

- `harness-os/backend/main.py`

Day 1 was expanded from a thin checklist into a fuller 85-minute course:

- More foundation concepts.
- More schedule blocks.
- RAG/evidence cards.
- sample materials.
- explicit required action.
- source verification and final-result storage expectations.

Evidence files:

- `docs/reports/completion_evidence/edu_day1_curriculum_restore_20260628.json`
- `docs/reports/completion_evidence/edu_day1_curriculum_ux_depth_20260630.json`

### Smartphone Wording

Core files:

- `harness-os/backend/main.py`
- `tests/test_edu_vp_training_flow.py`

Behavior:

- Runtime and legacy refresh paths normalize old `iPhone`, `iphone`, and `아이폰` copy to `스마트폰`.
- Existing saved Day 1 tutorial steps with `iPhone에서 장면 고르기` are rewritten to `스마트폰에서 장면 고르기`.
- The intentionally split string `"i" + "phone"` may still exist in source as a regression-test or normalization guard to avoid literal UI leakage. Do not mistake that for a visible product string.

Evidence files:

- `docs/reports/completion_evidence/edu_mobile_device_label_neutral_20260630.json`
- `docs/reports/completion_evidence/edu_mobile_device_iphone_literal_removed_20260630.json`
- `docs/reports/completion_evidence/edu_legacy_mobile_scene_snapshot_normalized_20260630.json`

### Day 1 Guided Practice Lab

Core files:

- `harness-os/backend/main.py`
- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/edu-app/src/lib/vpTraining.ts`
- `tests/test_edu_vp_training_flow.py`

Behavior:

- Added `practice_lab` payload to Day 1.
- Added frontend `Day1PracticeLab`.
- Replaced the vague "업무 장면 1개를 실제로 질문했다" style checklist with guided in-app steps:
  - open/read the practice lab first.
  - choose a source in-app.
  - remove sensitive information.
  - fill the prompt.
  - open/install the selected AI tool only at the right moment.
  - verify answer against source.
  - save four result slots.
- Added `practice_lab_version`.
- Added refresh migration for legacy incomplete Day 1 states without deleting existing proof text.

Evidence file:

- `docs/reports/completion_evidence/edu_day1_guided_practice_lab_20260630.json`

### Day 1 Images And Tool Installation Guidance

Core files:

- `harness-os/backend/main.py`
- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/edu-app/src/lib/vpTraining.ts`
- `tests/test_edu_vp_training_flow.py`

New image assets:

- `harness-os/edu-app/public/training/day1/prepare-material.svg`
- `harness-os/edu-app/public/training/day1/remove-private-info.svg`
- `harness-os/edu-app/public/training/day1/install-ai-app.svg`
- `harness-os/edu-app/public/training/day1/verify-answer.svg`

Behavior:

- Day 1 `practice_lab` now returns `visual_assets`.
- `Day1PracticeLab` renders a four-image strip near the top.
- Tool cards also render per-step images.
- A new `install_guide` explains what to do if the selected AI app is not installed.
- The installation guide is personalized by selected tool:
  - Claude: home screen search, `claude.ai` browser fallback, login/signup, input-box confirmation, optional store install.
  - ChatGPT: home screen search, App Store/Play Store install, `chatgpt.com` fallback, login/signup, input-box confirmation.
  - Gemini: Gemini/Google app search, store install, `gemini.google.com` fallback, Google login, input-box confirmation.
  - Other: official app/browser route, login/signup, input-box confirmation, stop before payments/private data if unsure.
- Version bumped to `2026-06-30-guided-images-v2` so incomplete legacy Day 1 states receive the visual/install lab.

Evidence file:

- `docs/reports/completion_evidence/edu_day1_training_images_visible_20260630.json`

## Current Expected Day 1 UX

When a user enters Day 1, the screen should retain the Day 0-style training tone and show:

- Day title and mission.
- detail card.
- why-learn section.
- today's mission.
- guided practice lab.
- four educational images:
  - 자료 먼저 고르기.
  - 민감정보 제거.
  - selected AI tool 열기.
  - 답변 검증.
- selected-tool install/open guidance.
- table explaining what happens inside this app vs inside the AI app.
- copyable prompt.
- source verification rows.
- result slot checklist.
- final paste area and completion button.

The user should not be left with only "go ask the app yourself" instructions.

## Verification Already Run

Local:

- `.venv/bin/python -m pytest tests/test_edu_vp_training_flow.py -q`
  - `114 passed, 3 warnings, 59 subtests passed`
- `npm run build --prefix harness-os/edu-app`
  - passed.
  - local dist copied all four SVG assets into `harness-os/edu-app/dist/training/day1/`.
- `npm run lint --prefix harness-os/edu-app`
  - passed.
- `.venv/bin/python scripts/agent_completion_guard.py docs/reports/completion_evidence/edu_day1_training_images_visible_20260630.json --require-deploy`
  - `completion_guard: CLEAR`
  - status: `complete`

Mac Mini / production:

- `scripts/deploy_to_macmini.sh ...`
  - selected paths deployed.
  - backend launchd reloaded.
  - selected path origin diff checks returned `0`.
- Mac Mini edu app rebuild:
  - `npm run build --prefix harness-os/edu-app`
  - built `dist/assets/index-DMOqjtLb.js`.
  - `launchctl kickstart -k gui/$uid/com.harness.edu-app` completed.
- Production URL checks:
  - `http://100.97.175.44:5174/training/day1/prepare-material.svg` returned HTTP `200`.
  - `http://100.97.175.44:5174/training/day1/remove-private-info.svg` returned HTTP `200`.
  - `http://100.97.175.44:5174/training/day1/install-ai-app.svg` returned HTTP `200`.
  - `http://100.97.175.44:5174/training/day1/verify-answer.svg` returned HTTP `200`.
  - `http://100.97.175.44:8000/api/health` returned `{"ok":true,...}`.
- Deployed backend payload check:
  - `_edu_vp_build_day1({"preferred_llm": "claude", ...})` returned:
    - `practice_lab_version=2026-06-30-guided-images-v2`
    - visual asset paths:
      - `/training/day1/prepare-material.svg`
      - `/training/day1/remove-private-info.svg`
      - `/training/day1/install-ai-app.svg`
      - `/training/day1/verify-answer.svg`
    - install guide title: `Claude를 처음 쓰는 경우`
    - install guide steps include `claude.ai`.

## Deployment Notes

Important detail:

- Mac Mini selected-path deploy validates selected files against `origin/main`.
- The Mac Mini repository HEAD observed after final deploy may not equal local HEAD because deploy uses selected checkout rather than whole-repo pull.
- In the final verification, selected deployed paths matched `origin/main`.

## If The User Still Says Images Are Not Visible

Check in this order:

1. Confirm the browser loaded the rebuilt bundle:
   - `curl -fsS http://100.97.175.44:5174/`
   - Look for `assets/index-DMOqjtLb.js` or a newer bundle.
2. Confirm SVG assets are served:
   - `curl -fsSI http://100.97.175.44:5174/training/day1/prepare-material.svg`
   - repeat for the other three SVGs.
3. Confirm the active training state is refreshed to Day 1 v2:
   - backend payload or saved state should show `practice_lab_version=2026-06-30-guided-images-v2`.
4. If a stale session still has old Day 1:
   - `_edu_vp_refresh_state` should migrate incomplete Day 1 states.
   - completed Day 1 states may not be rewritten by design; inspect state before changing completion behavior.
5. If frontend still hides images:
   - inspect `Day1PracticeLab` in `harness-os/edu-app/src/components/TrainingScreen.tsx`.
   - verify `visualAssets.length` and `toolCards[].image_src`.
6. If HTTP serves assets but the phone browser does not show them:
   - suspect cached JS/service state.
   - rebuild/restart edu-app and hard refresh.

## Suggested Next Loop

Priority if the user continues Day 1 UX review:

1. Use Playwright or in-app browser screenshot to verify actual rendered Day 1 on desktop/mobile widths.
2. Add stronger visual hierarchy if the image strip feels too small on mobile.
3. Add real app-logo-neutral guidance only if legally/brand-safe; current SVGs avoid brand logos.
4. Consider adding a small "설치가 막히면 여기까지만 체크" fallback state for users who cannot log in.
5. Add automated frontend test or screenshot smoke if the repo has an established browser-test path.

## Files Most Likely To Edit Next

- `harness-os/backend/main.py`
  - Day 1 payload, migration, install guide text.
- `harness-os/edu-app/src/components/TrainingScreen.tsx`
  - Day 1 visual layout and interaction.
- `harness-os/edu-app/src/lib/vpTraining.ts`
  - payload contracts.
- `tests/test_edu_vp_training_flow.py`
  - backend regression coverage.
- `harness-os/edu-app/public/training/day1/*.svg`
  - educational images.

## Do Not Touch Without User Direction

- Do not revert `docs/education/edu_parents_first_parent_landing.html`; it was already dirty/unrelated.
- Do not reintroduce visible `iPhone` copy in Day 1.
- Do not remove the selected-tool install guide.
- Do not weaken Day 0 safety confirmation semantics while fixing Day 1 UX.
- Do not mark production complete without completion evidence guard and a user-facing/runtime check.
