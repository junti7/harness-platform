# Claude review — Saju follow-up cache routing

- Verdict: `CLAUDE_CLEAR`
- Scope: staged follow-up routing, cache-key, plugin-tool, and process-lifecycle changes
- Confirmed: unclassified intents no longer collide; stdin protects birth data from argv; bounded run/session enforcement blocks direct NotebookLM during Saju turns; child termination is guarded.
- Follow-up addressed: verified OpenClaw hook context fields from installed runtime documentation and added a stateful hook lifecycle test.
- Residual risk: outside an active Saju turn, obfuscated shell indirection is not treated as a security boundary.

