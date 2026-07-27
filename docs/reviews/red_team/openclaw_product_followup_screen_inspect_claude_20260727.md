# OpenClaw product follow-up screen-inspect Red Team — Claude

Date: 2026-07-27
Reviewer: Antigravity `claude-sonnet-4-6`
Verdict: `red_team_clear`

Scope:

- `plugins/harness-bridge/index.js`
- `tests/test_harness_bridge_plugin.mjs`

Prompt:

Review the diff that routes product/detail follow-up questions such as "어떤 제품들이 보여?" to `harness_screen_inspect` when a recent trusted screen-inspect trajectory exists, and prefers Coupang/쿠팡 Chrome windows in the read-only Peekaboo fallback when Coupang context is present.

Findings:

- Owner gate remains intact; the new route is only reached after owner detection.
- High-impact browser action filtering remains active for the new detail-followup branch.
- No trajectory content is injected; the context prefix is a static literal.
- Window preference changes target ranking only; no write/click/type/browser action is introduced.
- Fallback capture remains read-only and scoped.
- Added negative regression tests for standalone detail follow-up and add-to-cart phrasing.

Conclusion:

`red_team_clear`; no blocking safety regression found.

Incremental v2 review:

- Change: apply the static Coupang/Chrome context prefix to any already-routed product/detail follow-up, not only trajectory-routed follow-ups.
- Verdict: `red_team_clear`.
- Reason: `markScreenInspectRun` is reached only after `shouldEnforceScreenInspect` has already passed; the static prefix adds no prompt-injection surface, high-impact browser action leakage, network call, file I/O, or privilege escalation.
