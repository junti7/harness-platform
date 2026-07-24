# OpenClaw Saju expert/cache Red Team — Copilot

- Date: 2026-07-24
- Model: GitHub Copilot CLI 1.0.74
- Mode: read-only, no tools
- Scope: generalized Saju expert answer contract, Asia/Seoul relative dates,
  relay minimization, private semantic cache, invalidation, concurrency, and
  failure recovery.

## Final result

- BLOCKER: none
- MAJOR: none
- MINOR: audit coverage for pre-query relative-date errors and corrupt cache
  reads could be more granular; compound relative-date idioms remain a narrow
  language edge case.
- Verified: relay fail-closed, 0700/0600 cache permissions, bounded
  single-flight, source-revision invalidation, and degraded cache operation.
- Production follow-up: after `notebook.updated_at` proved conversation-mutated,
  the cache revision changed to a stable sorted source-identity hash. Copilot
  re-reviewed the follow-up with no blocker or major finding. Same-ID in-place
  source changes remain bounded by the hard six-hour TTL.

VERDICT: clear
