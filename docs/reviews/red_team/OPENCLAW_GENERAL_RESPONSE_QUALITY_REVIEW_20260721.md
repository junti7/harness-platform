# Red Team Verdict — OpenClaw General Response Quality

- Date: 2026-07-21
- Artifact: `docs/strategy/OPENCLAW_GENERAL_RESPONSE_QUALITY_REBUILD_20260721.md`
- Reviewers: Claude Sonnet CLI + GitHub Copilot CLI + Codex code-trace adjudication
- Overall verdict: `red_team_block`
- President mediation required: no; implementation evidence is absent

## Model verdicts

| Reviewer | Verdict | Principal reason |
| --- | --- | --- |
| Claude Sonnet | `red_team_block` | Target architecture is unimplemented; tool evidence, direct fallback, and unstructured partial delivery remain open |
| GitHub Copilot CLI | `red_team_block` | Route evidence spoofing, no claim verifier, async outbound bypass, and split authorization metadata |
| Codex adjudication | `red_team_block` | Common blocking findings reproduced in code; one claimed auth exploit narrowed to drift risk |

## Non-negotiable blockers

1. Route name is still treated as evidence.
2. Material factual claims have no claim-level provenance.
3. Current-fact requests can reach an unverified default contract.
4. Background Slack delivery can bypass the response verifier.
5. Partial/abstain is not a machine-enforced delivery state.
6. Release metrics are not produced by an executable corpus scorer.

## Adjudicated disagreement

Copilot identified `goal-model` as an authorization inconsistency. The code has conflicting declarations: `_is_mutating_intent` calls it mutating, while `ACTION_REGISTRY` calls its default form read-only. The classifier can only emit the read-only form, while registration with `--equation` is available through the structured path and receives CEO authorization. Therefore no present write bypass was proven for this example. The duplicate policy remains a high-severity drift risk.

## Clear conditions

`red_team_clear` requires all of the following:

- implemented typed contract, evidence item, claim ledger, and delivery decision;
- one canonical authorization registry across all routes;
- all user-visible outbound paths behind the same verifier;
- executable adversarial corpus and machine-readable scoring artifact;
- zero unsupported factual finals, stale definitive claims, unauthorized mutations, and partial/abstain conversions;
- production shadow run for at least seven days or 200 representative read-only requests, whichever is later;
- actual Slack DM-path canary and rollback verification;
- new independent Claude + Copilot review of the implementation and runtime evidence.

Until these conditions are met, the existing guard may be described only as a baseline sanitizer and formatter.
