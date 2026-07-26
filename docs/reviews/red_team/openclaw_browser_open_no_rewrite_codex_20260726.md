`red_team_clear`

No blocking findings.

Verified in current patch:
- `before_tool_call` no longer rewrites params for browser-open; approved exact Coupang URL returns `undefined`.
- Phishing URL blocks with required Coupang URL.
- Internal execution authorization is stored by runId/context runId only.
- Direct/fake calls without runId fail before authorization.
- Same-session call without runId still fails after authorization.
- Repeated routed call blocks.
- Unsafe shell/browser paths remain blocked.

Ran: `node tests/test_harness_bridge_plugin.mjs` passed.

Follow-up cleanup applied after review: stale `routingToken` schema was removed while fake token execution still fails closed.
