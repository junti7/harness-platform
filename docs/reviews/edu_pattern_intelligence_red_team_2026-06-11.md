# Edu Pattern Intelligence Red Team

Date: 2026-06-11
Artifact reviewed: `docs/handoffs/edu_pattern_intelligence_plan_2026-06-11.md`
Prompt artifact: `docs/reviews/edu_pattern_intelligence_red_team_prompt_2026-06-11.txt`

## Model Outputs

### Claude Code (`claude` CLI)

- Verdict: `CONDITIONAL`
- Strongest findings:
  - demographic fields flowing into runtime opener/reply shaping create stereotype-overreach risk
  - transcript-derived patterns can become self-reinforcing after runtime injection without holdout validation
  - `monetization_signal` inside the main score mixes business desirability with human pain ranking
  - no explicit PIPA / minors / retention / PII scrubbing gate existed in the first draft
  - runtime injection required stronger gate than Red Team + Fact Check alone

### Gemini CLI (`gemini` CLI)

- Verdict: `BLOCK`
- Strongest findings:
  - demographic patternization has high stereotype/bias risk if sensitive attributes are weakly sourced
  - LLM-mediated Red Team must not be treated as the only ethical gate
  - runtime reuse can amplify bias and steer live answers in manipulative ways
  - `what_people_really_mean`-style fields can drift into over-interpretation
  - recurring review cadence needs explicit human review ownership and cost

## Accepted Changes

The implementation plan was updated to reflect the overlapping findings:

1. inferred demographics are now descriptive-analysis only and excluded from runtime biasing
2. `monetization_signal` was removed from the main pattern score and split into a separate business field
3. holdout / independence checks were added to prevent self-confirming transcript loops
4. `qa_clear`, `legal_review_approve`, and CEO/VP sign-off were added before any live runtime injection
5. PII scrubbing, retention, consent/legal review, and self-stated-vs-inferred attribute rules were added
6. approved patterns now require TTL / expiry and revalidation
7. complaint and dissatisfaction signals were elevated into a first-class improvement loop so repeated answer failures are explicitly tracked and prevented

## Consolidated Verdict

`red_team_conditional_clear`

Interpretation:

- Phase 1-3 (`fact extraction`, `candidate scoring`, `review queue`) can proceed.
- Phase 4 (`runtime answer shaping`) is blocked unless the stronger gating and data-governance constraints added above are implemented first.
