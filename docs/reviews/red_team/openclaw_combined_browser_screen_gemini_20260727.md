# OpenClaw combined browser-open + screen-inspect Red Team — Gemini

Date: 2026-07-27
Reviewer: Antigravity `gemini-3.6-flash-low`
Verdict: `red_team_clear`

Scope:

- `plugins/harness-bridge/index.js`
- `tests/test_harness_bridge_plugin.mjs`

Prompt:

Review the diff for safety regressions, owner-gating bypass, high-impact browser action allowance, and whether the requested fix is correctly scoped. Expected behavior: owner request "open Coupang in browser, tell me what is visible, and if Coupang is visible check whether login status is visible" should bind and allow exactly `harness_browser_open` then `harness_screen_inspect`. It must not allow login, checkout, payment, add-to-cart, shell, `web_fetch` fallback, or non-owner execution.

Findings:

- `HIGH_IMPACT_BROWSER_ACTION` relaxation correctly distinguishes read-only login-status checks from login/action requests.
- Combined route remains owner-gated through `ownerRequest`.
- Tool-call enforcement blocks `harness_screen_inspect` before `harness_browser_open`.
- Combined route blocks `web_fetch`, shell, browser automation bypass, login, checkout, payment, and form actions.
- Tests cover combined routing, order violation, fallback blocking, and negative high-impact cases.

Conclusion:

`red_team_clear`; no owner-gating bypass, high-impact browser action leakage, or material safety regression found.
