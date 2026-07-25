# Smartfarm dashboard plan - Codex RED TEAM

- Reviewer: Codex
- Artifact: `docs/plans/SMARTFARM_DASHBOARD_IMPLEMENTATION_PLAN_20260725.md`
- Initial verdict: `red_team_block`

## Material findings

1. MQTT command ordering, duplicate delivery, retained replay, and backend restart recovery were underspecified.
2. Retained status without LWT and heartbeat deadline could produce false-green health.
3. SQLite needed a single-writer contract, explicit retention, backup, and restore verification.
4. MQTT identity/ACL/TLS and secret-handling boundaries were absent.
5. ON required fresh re-authentication rather than only a long-lived Harness session.
6. Emergency OFF needed a control-plane-independent Pi-local and physical path.
7. Sensor tests and actuator/GPIO tests needed separate permissions and lockouts.
8. Clock skew and boot-scoped sequence handling were missing.

## Required resolution

All eight findings must be added to the plan and verified with fault injection. Until independent
Gemini re-review also clears the revised plan, status remains `red_team_block`.
