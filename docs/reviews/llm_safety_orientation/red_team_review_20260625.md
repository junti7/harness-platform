# LLM Safety Orientation Red Team Review - 2026-06-25

artifact: `docs/education/llm_safety_orientation_script_20260625.md`
code:
- `harness-os/backend/main.py`
- `harness-os/edu-app/src/components/TrainingScreen.tsx`
- `harness-os/edu-app/src/lib/vpTraining.ts`
- `harness-os/frontend/src/pages/EduVpTrainingPage.tsx`
- `tests/test_edu_vp_training_flow.py`

## Verdict

`red_team_clear`

## Model Review Trail

### Copilot CLI

Initial verdict: `red_team_block`

Blocking findings:
- Stigmatizing mental-health/vulnerable-user wording.
- Personalized Day 0 schedule missed explicit safety-boundaries block.
- Safety confirmation was local UI state only.
- Backend completion gate initially trusted client-provided `safety_confirmed`.
- Legacy `harness-os/frontend` training page bypassed the new safety gate.

Fixes applied:
- Replaced stigmatizing wording with neutral help-seeking language.
- Added explicit `안전 사용 기준 확인` block to personalized Day 0.
- Persisted confirmation in `ui_state.safety_confirmed`.
- Changed backend to compute safety confirmation from current Day 0 required `understand_*` checklist ids and `confirmed_check_ids`, rather than accepting a client boolean.
- Added `/artifact` guard: Day 0 completion is rejected unless backend-computed safety confirmation exists.
- Added gate to both active frontend surfaces:
  - `harness-os/edu-app/src/components/TrainingScreen.tsx`
  - `harness-os/frontend/src/pages/EduVpTrainingPage.tsx`

Final Copilot verdict: `red_team_clear`

### Codex Review

Verdict: `red_team_clear`

Notes:
- The script now avoids long transcript quotation and discloses failed subtitle ingestion.
- The learner-facing order is preserved: risk explanation, LLM generation principle, safety boundaries, explicit confirmation, then practice.
- Frontend practice/preview/proof/completion controls are hidden before confirmation in both active training surfaces.
- Backend no longer stores a raw client-provided `safety_confirmed: true` as authoritative.

### Claude CLI Gap

Claude CLI was available and authenticated, but both review attempts failed to return a usable artifact:

- Long file-reading review: hung for more than 90 seconds, interrupted.
- Short summary review with `haiku`: hung for more than 60 seconds, interrupted.

Because Claude output was not recovered, this memo should not be represented as a Claude-produced review artifact. The practical Red Team pass for this implementation is Copilot + Codex, with the Claude availability gap recorded here.

## Residual Risk

The system can verify that the user clicked all required confirmation items; it cannot prove the user truly read or understood the material. This is acceptable for the current training UX but should be paired with VP/human observation for high-risk learner groups.

## Transcript Update Review

After the President provided the time-coded Korean transcript, the script was updated to cover additional risk patterns:

- AI sycophancy / always-on agreement and praise.
- Unsafe acceleration into real-world decisions such as money, work, business, and family-impacting choices.
- Guardrail limitations without reproducing bypass methods.
- Minors and character chatbot exposure.
- Reality-brake signals: sleep, food, money, work, and family consultation.

Additional implementation hardening:

- Default Day 0 backend payload is now safety-only.
- Practice content is not shipped as `post_safety_practice` before confirmation.
- Practice schedule and first-prompt copy are generated only after backend validation of `confirmed_check_ids`.

Copilot CLI final verdict after transcript update: `red_team_clear`

Blockers: none.
