# Claude Red Team Review — OpenClaw screen inspect fail-fast

Date: 2026-07-27

Model: `claude-sonnet-4-6` via `agy`

Status: `red_team_clear`

Summary:
- Owner gating passes: routing requires `currentSenderIsOwner()` and `shouldEnforceScreenInspect()`.
- Direct unrouted calls cannot mint an execution token.
- Peekaboo shell bypass is blocked during screen-inspection routing.
- All Peekaboo stages have explicit timeouts: bridge status 3 seconds, permissions 3 seconds, screen inspection 15 seconds.
- The implementation is read-only and does not introduce click, type, login, cart, order, purchase, payment, or form-submit actions.

Reviewer output excerpt:
> `red_team_clear`
>
> All four focus areas pass. The implementation is a faithful port of the `harness_browser_open` two-phase gating pattern with appropriate read-only constraints, bounded timeouts at every async stage, and shell/Peekaboo bypass blocking tested with a concrete evasion case. No click, type, buy, or data-leak vectors introduced.

Non-blocking note:
- Real screen inspection still requires the OpenClaw GUI bridge socket and macOS Screen Recording/Accessibility permissions to be present at runtime.
