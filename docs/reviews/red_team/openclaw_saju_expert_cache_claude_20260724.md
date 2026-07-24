# OpenClaw Saju expert/cache Red Team — Claude

- Date: 2026-07-24
- Model: Claude Sonnet via authenticated Claude CLI
- Mode: read-only, tools disabled
- Scope: generalized applicability, Asia/Seoul date handling, expert quality
  contract, relay minimization, cache freshness, privacy, concurrency, and
  recovery.

## Final result

- BLOCKER: none
- Verified: Saju-only expert contract, compact verbatim relay, source
  `updated_at` and source-count invalidation, missing-revision fail-closed,
  single-flight behavior, and graceful cache degradation.
- Residual observations: cache contract changes must bump
  `NOTEBOOKLM_CACHE_VERSION`; cache cleanup is query-triggered; rare Korean
  compound relative-date forms remain edge cases.

VERDICT: clear
