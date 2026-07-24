# OpenClaw hardware typo grounding — Copilot review

Scope: final staged implementation for model-identifier normalization, evidence ranking, Skill
instructions, tests, and completion evidence.

## Verdict

`VERDICT: clear`

## Source-authority ranking follow-up

Copilot blocked the first fixed-penalty proposal because it could erase the only available
auxiliary evidence. The implementation was replaced by lossless two-tier ordering. Explicit
Korean/English verification and review queries preserve original ranking, auxiliary-only
repositories retain fallback evidence, and domain-root boost is capped. Final re-review:

`VERDICT: clear`

## Findings addressed before release

- The initial review blocked global correction of arbitrary letter-plus-number identifiers.
- Correction is now gated by hardware intent, smartfarm repository roots, a registered model
  family, edit distance, and a unique-nearest match.
- Ambiguous, exact, repeated, unrelated ticket/version, and non-model GPIO cases fail safely.
- Wiring and network/protocol evidence are covered separately.

No blocker or major issue remained after the constrained implementation was re-reviewed.

## Production routing follow-up

The first production replay exposed a Skill-selection gap. Copilot independently reviewed the
hardware trigger and scoped fallback block after the repair and returned no finding.

`VERDICT: clear`
