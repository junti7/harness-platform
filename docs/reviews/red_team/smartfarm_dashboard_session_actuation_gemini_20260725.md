# Smartfarm Session Actuation RED TEAM — Gemini

- CEO order: remove password re-entry because the operator is already authenticated as CEO.
- Reviewer: Antigravity Gemini 3.6 Flash Low
- Initial verdict: `red_team_block`
- Initial finding: removing both password re-entry and the one-use nonce enabled replay.
- Remediation: retain the one-use nonce, but issue it automatically from a new CEO-role-protected session endpoint.
- Re-review verdict: `red_team_clear`

Verified controls:

- `POST /api/smartfarm/actuation/session-token` requires a valid CEO role token.
- The pump endpoint consumes the token once; replay returns 403.
- Exact zone confirmation remains required.
- TEST remains limited to 1–3 seconds.
- Feature flag, fresh watchdog, sensor-quality check, per-zone lock, Pi bounded timer, and observed automatic OFF are unchanged.
- Invasive diagnostics retain their existing nonce requirement.

Residual risk:

- An unlocked or compromised CEO session can request a token and initiate a bounded TEST.
- Role-token protection and origin policy remain part of the Harness OS security boundary.
