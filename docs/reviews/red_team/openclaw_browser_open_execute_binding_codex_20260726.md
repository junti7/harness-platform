red_team_clear

Scope: current execute binding patch after live replay returned `browser_open_not_bound_to_routed_owner_request`.

Findings:
- `before_tool_call` still performs owner-context routing, exact URL validation, and one-call state marking before any execution token is created.
- Execution authorization is still internal-only and short-lived; the model cannot forge it through params because `execute` ignores params for the final URL and uses the prevalidated token URL.
- Adding `toolCallId`, `toolUseId`, `itemId`, and `id` to execution keys binds the route to the same tool call identity rather than broad session state.
- Same `toolCallId` duplicate pretool checks remain idempotent; different or missing tool call IDs after the first call remain blocked.
- Local regression passed: `node tests/test_harness_bridge_plugin.mjs`, `.venv/bin/python -m pytest -q tests/test_openclaw_bridge.py`, `node --check plugins/harness-bridge/index.js`, and `git diff --check`.
