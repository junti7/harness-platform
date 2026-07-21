# OpenClaw General Quality Implementation — Copilot Red Team

- Date: 2026-07-21
- Model: GitHub Copilot CLI
- Mode: independent read-only review
- Verdict: `red_team_clear`

## Findings and resolution

1. `slack_listener._outbound_text` could evaluate `"error" in None` and crash a verified DM. Fixed with a null-safe comparison and regression test.
2. Copilot initially interpreted secret-masked source display as a hard-coded Slack bearer token. Direct source inspection and a monkeypatched HTTP regression test prove that the supplied function parameter is used as `Bearer {token}`. Copilot re-evaluated this as a masking artifact.

## Evidence

- Independent CLI review/resume: `27ab35fe-6849-42cd-b5eb-654d32596f74`
- Final verdict: `red_team_clear`, exploit none

## Production regression delta

- Copilot first blocked canonical subject replacement because it could let Turtle or ambiguous status requests consume generic Harness evidence.
- The replacement was removed; request metadata terms are filtered while named subjects remain.
- Copilot then found a Haiku classifier bypass for ambiguous status. The intent-bridge path now rejects `subject_missing`, and the E2E golden scorer deliberately exercises that classifier result.
- Delta re-review verdict: `red_team_clear` (session `37b6b259-ca00-49df-a63f-da36fec266a7`).
- Claude delta review was unavailable due CLI session limit HTTP 429; no false cross-model-clear claim is made for this delta.
