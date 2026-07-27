# OpenClaw combined browser-open + screen-inspect Red Team — Claude

Date: 2026-07-27
Reviewer: Antigravity `claude-sonnet-4-6`
Verdict: `red_team_clear`

Scope:

- `plugins/harness-bridge/index.js`
- `tests/test_harness_bridge_plugin.mjs`

Prompt:

Review the diff for safety regressions, owner-gating bypass, high-impact browser action allowance, and whether the requested fix is correctly scoped. Expected behavior: owner request "open Coupang in browser, tell me what is visible, and if Coupang is visible check whether login status is visible" should bind and allow exactly `harness_browser_open` then `harness_screen_inspect`. It must not allow login, checkout, payment, add-to-cart, shell, `web_fetch` fallback, or non-owner execution.

Findings:

- Owner-gating is intact; both browser-open and screen-inspect routing depend on `ownerRequest`.
- Passive login-status references are allowed, while imperative login and browser mutation actions remain blocked.
- Combined path allows only `harness_browser_open` followed by `harness_screen_inspect`.
- `web_fetch`, shell, Browser MCP, Playwright, direct Peekaboo, checkout, payment, and form actions are blocked by tool-call enforcement and system context.
- Regression tests cover happy path and ordering/bypass failures.

Conclusion:

`red_team_clear`; no safety regression or scope expansion detected.
