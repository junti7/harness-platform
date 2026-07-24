# Copilot Review — OpenClaw Harness Workspace Access

- Date: 2026-07-24
- Role: independent full-diff security and correctness review
- Scope: `plugins/harness-bridge/index.js` and plugin regression tests

Initial verdict: `block`

Findings fixed:

1. The initial generic command validator allowed Python/Node to mutate outside the repository.
2. The first allowlist revision trusted executable basenames, allowing a malicious `/tmp/git` or `/tmp/pytest`.

Final implementation restricts execution to trusted real executable paths, read-only Git subcommands, Node `.mjs` tests under `tests/`, and pytest targets under `tests/`.

Final verdict: `clear`

Final Copilot result: “The malicious executable-basename bypass is fixed by realpath trust checks before allowlisting (`git`/`node`/`pytest`) and I do not see any blocking security or correctness issue in these diffs.”
