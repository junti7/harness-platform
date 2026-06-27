# EDU AI Coach Answer Architecture Plan

Date: 2026-06-27
Owner: Codex
Status: Draft for external LLM diagnosis

## 1. Problem

The current EDU AI coach improved from its original weak state, but the improvement path has become too rule-heavy.

What changed so far:

- Bad answer patterns are now blocked by deterministic rules.
- Downvoted answers create reinforcement candidates.
- RAG evidence is retrieved and must be reflected when selected.
- Fast-template answers can include RAG.
- Latency guard prevents slow RAG from blocking deploy.
- Max simulation guard blocks regressions across corpus and adversarial cases.

Remaining concern:

- The system can drift into a FAQ/rule engine.
- Rules prevent bad answers, but they do not create creative, context-aware answers.
- The next stage must move from case-specific patches to structured answer reasoning.

## 2. Design Principle

Rules are safety rails, not the answer engine.

The answer engine should be model-driven and structured:

```text
question
→ intent/context analysis
→ RAG retrieval and synthesis
→ answer plan
→ final answer generation
→ verifier/guard
```

Rules should only enforce:

- safety boundaries
- forbidden failure modes
- latency budgets
- evidence grounding
- cache/version correctness

Rules should not decide the full answer shape except for emergency fallback.

## 3. Current Architecture

```text
question
→ policy/context lookup
→ reinforcement lookup
→ fast-template check
→ RAG retrieval
→ answer generation or fast fallback
→ red-team quality review
→ cache/event log
```

Strengths:

- Prevents repeated known bad answers.
- Handles empathy/cost/energy/principle failure modes better than before.
- Uses large simulation guard before deploy.
- Tracks whether RAG was actually reflected.
- Caps RAG latency.

Weaknesses:

- Fast-template still exists as a handcrafted path.
- RAG is often inserted as one sentence instead of shaping the whole answer.
- Creative answer quality is not directly scored.
- Intent analysis is split across many helper functions.
- More rules may increase brittleness.

## 4. Target Architecture

### Layer A: Intent and Context Model

Input:

- user question
- current lesson/concept
- prior downvote policy candidates
- user stage/day

Output JSON:

```json
{
  "surface_intent": "principle_question | emotional_support | cost_barrier | safety_boundary | practical_use | curiosity",
  "latent_need": "what the user is really asking",
  "risk_level": "low | medium | high",
  "answer_style": "empathetic | explanatory | coaching | cautionary",
  "must_answer_now": true,
  "avoid_patterns": ["cold_redirect", "definition_only"],
  "creative_angle_needed": true
}
```

Purpose:

- Replace scattered case logic with one structured intent object.
- Still allow deterministic override for high-risk safety cases.

### Layer B: RAG Synthesis

Input:

- selected evidence items from YouTube/RSS/community/corpus
- intent/context object

Output JSON:

```json
{
  "usable": true,
  "fresh_angle": "new perspective from collected data",
  "reader_relevance": "why this matters to a parent/learner",
  "example_seed": "realistic example to use in answer",
  "evidence_risk": "none | weak_match | stale | source_low_confidence"
}
```

Purpose:

- RAG should not be pasted.
- RAG should change the angle, example, or practical advice.
- If RAG is weak, skip it quickly and record why.

### Layer C: Answer Plan

Input:

- intent/context object
- RAG synthesis
- lesson concept

Output JSON:

```json
{
  "opening_move": "acknowledge | direct_answer | contrast_misconception",
  "core_explanation": ["point 1", "point 2"],
  "fresh_example": "example grounded in RAG or user context",
  "boundary": "what not to overtrust",
  "closing_rule": "one memorable criterion"
}
```

Purpose:

- LLM thinks before writing.
- Final answer becomes structured but not rigid.
- Same question can receive different answers as RAG and context change.

### Layer D: Final Answer Generation

Input:

- answer plan
- style constraints
- max length

Output:

- 3-5 natural Korean sentences.
- No prompt labels.
- No cold lecture.
- No unsupported evidence claims.

### Layer E: Verifier

Checks:

- Directly answers user question.
- Uses selected RAG if RAG synthesis says usable.
- Does not use unsupported RAG.
- Has empathy when emotional.
- Does not contradict user constraint.
- Meets latency and length budget.
- Avoids known downvoted pattern.

Verifier can be hybrid:

- deterministic checks for safety and latency
- small LLM judge only when ambiguity is high
- no LLM judge on fast low-risk paths unless needed

## 5. Latency Budget

Target budgets:

| Path | Target |
| --- | --- |
| Fast fallback, no RAG | < 300ms server-side |
| Fast path with RAG timeout | < 600ms server-side |
| Normal model answer | < 4s server-side |
| Retry path | avoid unless quality-critical |
| LLM judge | off by default, only ambiguous/high-risk |

Current deployed guard:

- fast RAG timeout must stay <= 450ms in guard simulation
- fast-template must call LLM 0 times
- RAG patch path must call LLM <= 1 time

## 6. Rollout Plan

### v16: Structured Intent Object

Goal:

- Add one internal intent/context JSON builder.
- Keep existing rules as fallback and verifier.
- Do not remove current safety logic yet.

Acceptance:

- Existing max guard still passes.
- Unit tests cover emotional, cost, energy, principle, practical, and curiosity cases.
- No latency increase over v15/vcurrent.

### v17: RAG Synthesis Object

Goal:

- Convert selected evidence into `fresh_angle`, `example_seed`, and `reader_relevance`.
- Stop treating RAG as only a sentence to append.

Acceptance:

- If RAG usable, final answer changes at least one of: angle, example, practical advice.
- If RAG weak, skip without delay.
- `evidence_used` means actual semantic use, not just selected.

### v18: Answer Plan Before Answer

Goal:

- Generate structured answer plan before final Korean answer.
- Final answer follows the plan but remains natural.

Acceptance:

- No cold/robotic plan labels leak into final answer.
- Answer variety increases across similar questions.
- Guard catches plan-answer mismatch.

### v19: Creativity Evaluation

Goal:

- Add evaluation dimension beyond safety: useful novelty.

Rubric:

- directness
- empathy
- accuracy
- RAG grounding
- practical usefulness
- fresh angle
- memorable example

Acceptance:

- Simulation output includes creativity/freshness score.
- Low creativity does not always block deploy, but trend is visible.

## 7. Rule Usage Policy

Allowed rules:

- high-risk safety blocks
- must-not-say phrases
- latency caps
- evidence grounding checks
- known downvote pattern rejection
- cache invalidation/versioning

Discouraged rules:

- exact answer templates for broad user questions
- per-question hardcoded answers
- endless keyword branches that decide content
- rules that replace RAG synthesis or answer planning

## 8. Red-Team Questions For External LLM

Ask external LLM to evaluate:

1. Does this plan actually move away from rule-based FAQ behavior?
2. Is the proposed intent/context layer too complex or still too rule-like?
3. How should RAG synthesis influence answer planning without increasing latency too much?
4. What failure modes remain if rules are only safety rails?
5. What minimal v16 implementation would prove the architecture works?
6. What should be measured to detect whether answers are genuinely more creative?
7. Where could this plan create hallucination or over-personalized coaching risk?

## 9. Current Implementation References

Primary files:

- `harness-os/backend/main.py`
- `scripts/check_edu_coach_simulation_regression.py`
- `scripts/edu_coach_simulation_runner.py`
- `scripts/edu_coach_corpus_scenario_generator.py`
- `tests/test_edu_vp_training_flow.py`
- `tests/test_edu_coach_simulation_regression_guard.py`

Recent deployed commits:

- `67c5d71 feat: infuse edu coach answers with rag evidence`
- `81bf5a3 test: require selected rag in edu coach answers`
- `dc3e210 perf: cap edu coach rag latency`
- `066c3d9 test: guard edu coach rag latency`

Current known resource gap:

- Claude CLI session limit until 2026-06-27 21:30 KST.
- Copilot CLI quota 0.
- Gemini red-team excluded until configured and credit restored.

## 10. Decision Needed

Before more code changes, decide:

- Proceed with v16 structured intent object first.
- Or revise architecture based on external LLM critique.
- Avoid adding more case-specific rules unless they are safety-critical.
