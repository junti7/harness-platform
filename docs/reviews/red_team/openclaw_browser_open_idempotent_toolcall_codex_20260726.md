red_team_clear

Findings: none blocking.

Checked:
- Same `harness_browser_open` `toolCallId` retry allowed: yes.
- No `toolCallId` repeat blocked: yes.
- Different `toolCallId` repeat blocked by same branch, though not explicitly asserted in test.
- RunId-only execution auth remains: direct same-session execute fails.
- Params are not rewritten by this fix.
- Unsafe shell blocks remain covered.

Verification: `node tests/test_harness_bridge_plugin.mjs` passed.
