# Codex Red Team Review — OpenClaw screen inspect fail-fast

Date: 2026-07-27

Status: `red_team_clear`

Scope:
- `plugins/harness-bridge/index.js`
- `plugins/harness-bridge/openclaw.plugin.json`
- `plugins/harness-bridge/skills/harness-control/SKILL.md`
- `tests/test_harness_bridge_plugin.mjs`

Findings:
- Owner routing is required before `harness_screen_inspect` can execute. Direct calls without a routed execution token return `screen_inspect_not_bound_to_routed_owner_request`.
- Screen inspection is inspect-only. The tool runs only `peekaboo bridge status`, `peekaboo permissions`, and `peekaboo see`; it does not click, type, submit forms, buy, pay, or log in.
- Shell-based Peekaboo access is blocked during screen-inspection routing, preventing the prior hanging `peekaboo` shell path from recurring.
- Fail-fast behavior is bounded: bridge status and permissions use 3-second limits; screen analysis uses a 15-second limit.
- Missing bridge socket and missing macOS permissions are surfaced as explicit operational blockers instead of guessed screen content.

Residual risk:
- A real screen description still depends on the OpenClaw GUI bridge being active and macOS Screen Recording/Accessibility permissions being granted by the user in the GUI.
