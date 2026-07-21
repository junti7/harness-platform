# Copilot Red Team — OpenClaw General Response Quality Rebuild

- Date: 2026-07-21
- Reviewer: GitHub Copilot CLI 1.0.73
- Review mode: independent, read-only
- Verdict: `red_team_block`

## Findings

1. Route labels currently act as evidence and permit irrelevant tool/runtime output to appear verified.
2. There is no per-claim proof of subject, time, requested dimension, authority, freshness, or coverage.
3. Generative formatting can alter factual output after evidence retrieval without verifying the transformed claims.
4. Authorization metadata is split across structured-command, action-registry, intent, tool, and orchestration paths, creating bypass and drift risk.
5. Background orchestration posts its result directly to Slack without the shared response verifier.
6. Freshness is detected by regex rather than enforced against evidence timestamps and source-specific SLA.
7. There is no structured fail-closed `abstain` state.
8. Tests do not establish claim provenance, stale-evidence blocking, cross-route authorization invariants, or async Slack delivery integrity.

## Required release conditions

- Replace route-name evidence inference with typed, normalized evidence.
- Add a deterministic per-claim verifier.
- Use one canonical authorization gate for every execution path.
- Route every outbound user-visible message through `DeliveryDecision`.
- Prove zero unsupported factual finals, stale definitive claims, authorization violations, and partial/abstain normalization on the evaluation corpus.
- Complete at least seven days or 200 representative read-only shadow requests, whichever is later, with no critical-family failure.

## Follow-up resolution

The review's `goal-model` example was traced after the independent pass. The classifier path builds only the read-only invocation, so a current write exploit was not demonstrated there. The duplicated authorization sources remain a valid structural risk and must still be consolidated.
