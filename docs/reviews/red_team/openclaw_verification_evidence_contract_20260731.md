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

The first production replay then exposed a remaining lifecycle mismatch: agent routing state
was keyed only by `runId`, while the executed screen tool retained the owner `sessionKey`.
Gemini blocked an initial token-only fallback because active state creation and cleanup still
used run-only keys. The implementation now uses one `runId + sessionKey + sessionId` key set
for screen-state creation, lookup, and deletion, and removes every execution token referencing
the cleared state. Plugin and Python regressions passed, and Gemini's independent incremental
review returned `red_team_clear`. This incremental fix preserves the earlier Claude clear while
addressing the production-only binding condition without weakening owner-session isolation.

The second production replay successfully captured and OCR-inspected the real Chrome window,
but exposed that outbound delivery hooks do not reliably carry the same context fields as the
agent lifecycle. Gemini blocked session-only correlation because overlapping turns could borrow
evidence. The final implementation permits attachment selection only through the exact
`sessionKey + runId`, then correlates `message_sent` cleanup with `sessionKey + SHA-256(final
outbound text)`. Expiry cleanup removes both pending and dispatched references. Regression tests
cover outbound delivery context without a context-level run ID. Gemini returned
`red_team_clear` after these changes.

Live Discord read-back showed that this durable delivery path omitted `runId` even at
`reply_payload_sending`. The final fallback therefore accepts a session-only match only when
that owner session has exactly one pending evidence state; zero or multiple states fail closed.
Gemini independently returned `red_team_clear` for this ambiguity guard and content-hash cleanup.

Because the deployed CLI delivery path bypassed `reply_payload_sending` entirely, the owner-bound
screen tool now sends the deterministic answer and first capture through OpenClaw's official
message command, confirms JSON delivery success, and immediately trashes every generated capture.
This path additionally requires `isOwnerOnlyDiscordSession`; the CEO's standing evidence
instruction is the explicit opt-in. Gemini blocked the initial session-string-only version and
returned `red_team_clear` after the authenticated owner allowlist gate was added.

## Residual risk

- A same-user local process with permission to alter Peekaboo output files can still interfere with
  the host generally. The plugin limits attachment and cleanup to exact generated filenames,
  regular single-link files, allowed roots, and captured device/inode identity.
- A screenshot can contain sensitive information visible on the CEO's own screen. It is marked
  `sensitiveMedia`, attached only to the owner-bound verification reply, and moved to Trash after
  delivery.
