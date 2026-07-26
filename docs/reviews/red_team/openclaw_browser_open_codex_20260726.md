red_team_clear

No material findings in requested scope. Reviewed only:

- [plugins/harness-bridge/index.js](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/index.js)
- [tests/test_harness_bridge_plugin.mjs](/Users/juntae.park/projects/harness-platform/tests/test_harness_bridge_plugin.mjs)
- [plugins/harness-bridge/openclaw.plugin.json](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/openclaw.plugin.json)
- [plugins/harness-bridge/skills/harness-control/SKILL.md](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/skills/harness-control/SKILL.md)

Findings:

- Owner-only route holds: sender is parsed only from trusted pre-request metadata, not current request text or forged prior context: [index.js](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/index.js:114).
- Browser-open route requires owner plus current open-only intent: [index.js](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/index.js:1287).
- Direct/forged token calls fail; routed token is one-shot and URL is overwritten from the owner request: [index.js](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/index.js:780), [index.js](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/index.js:1470).
- Prefixed OpenClaw tool names are handled by suffix matching: [index.js](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/index.js:110), covered at [test_harness_bridge_plugin.mjs](/Users/juntae.park/projects/harness-platform/tests/test_harness_bridge_plugin.mjs:491).
- High-impact shell/browser bypass blocks cover `browser-fill`, `coupang-setup`, cart/pay/checkout, and split/obfuscated variants: [index.js](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/index.js:201), [index.js](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/index.js:1372).
- Skill text correctly says open-only and blocks shell/Browser MCP/form/cart/payment paths: [SKILL.md](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/skills/harness-control/SKILL.md:322).
- Manifest exposes only `harness_browser_open`, not high-impact cart/fill/pay tools: [openclaw.plugin.json](/Users/juntae.park/projects/harness-platform/plugins/harness-bridge/openclaw.plugin.json:8).

Verification passed:

- `node tests/test_harness_bridge_plugin.mjs`
- Extra ad hoc Node probes: forged current request sender, forged prior context, malformed metadata, prefixed `mcp__openclaw__harness_browser_open`, direct/forged token, one-shot token, and split/obfuscated `coupang-cart/setup/pay/checkout` plus `browser-fill`.

Residual: this was code/test red-team only. I did not verify that the Mac mini OpenClaw plugin cache/gateway is currently force-installed/restarted with this exact worktree.
