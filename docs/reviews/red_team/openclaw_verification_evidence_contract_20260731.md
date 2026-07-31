# OpenClaw Verification Evidence Contract Red Team

Date: 2026-07-31
Artifact: `plugins/harness-bridge/index.js`, harness-control skill, regression tests
Status: `red_team_clear`

## Reviewers

- Antigravity Gemini 3.6 Flash Low
- Claude Sonnet 4.6
- Antigravity GPT-OSS 120B Medium (additional independent review)

## Review history

Gemini initially returned `red_team_block` for:

- a failure reply that could omit the evidence-failure marker;
- cleanup timer and cross-device move risks;
- overly broad verification intent;
- raw error/path disclosure;
- arbitrary local media attachment;
- unrelated tool calls counting as evidence;
- run-ID-only pending state;
- OCR mention/Markdown injection.

All findings were addressed with:

- deterministic failure composition;
- timer cancellation and expiry cleanup;
- exact generated-capture filename/root/type/link validation;
- device/inode identity checks and no unsafe EXDEV unlink fallback;
- narrower imperative intent matching;
- safe error-code mapping;
- question-to-tool evidence relevance;
- `sessionKey + runId` pending keys;
- outbound OCR and strict price sanitization.

Final Gemini verdict: `red_team_clear`.

Claude initially blocked UUID scoping, failed-inspection retry, Desktop capture provenance,
Markdown evidence escaping, and EXDEV cleanup. After remediation Claude returned
`red_team_clear`.

GPT-OSS independently reviewed the final diff and also returned `red_team_clear`.

## Residual risk

- A same-user local process with permission to alter Peekaboo output files can still interfere with
  the host generally. The plugin limits attachment and cleanup to exact generated filenames,
  regular single-link files, allowed roots, and captured device/inode identity.
- A screenshot can contain sensitive information visible on the CEO's own screen. It is marked
  `sensitiveMedia`, attached only to the owner-bound verification reply, and moved to Trash after
  delivery.
