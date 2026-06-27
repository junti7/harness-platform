# EDU AI Coach Answer Architecture Plan

Date: 2026-06-27
Owner: Codex
Status: Revised after external LLM diagnosis

External diagnosis source:

- `/Users/juntae.park/.gemini/antigravity-cli/brain/4b399019-8d81-423e-86a5-73bf0a01312b/answer_architecture_plan_diagnosis.md`

Main correction from diagnosis:

- Do not implement a sequential 3-4 LLM-call layer chain.
- Use one bounded structured generation call for intent + RAG synthesis + answer plan + final answer.
- Keep deterministic rules as guardrails and policy registry runtime, not as the answer engine.
- Make this document subordinate to the Digital Twin Robustness Plan taxonomy and policy system.

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

The answer engine should be model-driven and structured, but not multi-call by default:

```text
question
→ deterministic safety/policy precheck
→ bounded RAG retrieval
→ one structured LLM call that returns intent + RAG synthesis + answer plan + final answer
→ deterministic verifier/guard
→ optional LLM judge only for ambiguous/high-risk failure cases
```

Rules should only enforce:

- safety boundaries
- forbidden failure modes
- latency budgets
- evidence grounding
- cache/version correctness

Rules should not decide the full answer shape except for emergency fallback.

## 2.1 Canonical Relationship To Digital Twin Robustness Plan

This document does not replace `docs/education/EDU_AI_COACH_DIGITAL_TWIN_ROBUSTNESS_PLAN_2026-06-27.md`.

Canonical ownership:

| Concern | Canonical owner |
| --- | --- |
| intent/failure taxonomy | Digital Twin Robustness Plan |
| policy registry and must/must-not contracts | Digital Twin Robustness Plan + `configs/education/edu_coach_policy_registry.json` |
| simulation/corpus generation | Digital Twin Robustness Plan |
| runtime answer-generation architecture | this document |
| latency and deploy regression guard | `scripts/check_edu_coach_simulation_regression.py` |

Therefore:

- This plan must reuse the robustness taxonomy instead of defining an independent intent schema.
- New runtime intent fields are an answer-generation view of the existing taxonomy.
- Any new failure code must be added to the taxonomy/policy registry or explicitly marked experimental.
- If this document conflicts with the Digital Twin Robustness Plan on taxonomy, the robustness plan wins.

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

### 4.1 Single-Call Structured Answer Packet

Input:

- user question
- current lesson/concept
- prior downvote policy candidates
- user stage/day
- selected RAG evidence, if retrieved within budget
- policy registry context from robustness taxonomy

Output JSON from a single LLM call:

```json
{
  "taxonomy": {
    "topic_domain": ["ai_principle"],
    "user_need": ["explanation"],
    "constraint_type": [],
    "emotion_state": [],
    "risk_level": "low",
    "answer_shape": ["direct_answer", "simple_example"]
  },
  "runtime_intent": {
    "primary": "principle_question",
    "secondary": [],
    "latent_need": "explain mechanism without deflecting to curriculum",
    "answer_style": "plain_explanatory",
    "must_answer_now": true
  },
  "rag_synthesis": {
    "usable": true,
    "fresh_angle": "how current parent/learner content frames this issue",
    "reader_relevance": "why this matters for practice",
    "example_seed": "short practical example",
    "evidence_risk": "none"
  },
  "answer_plan": {
    "opening_move": "direct_answer",
    "core_explanation": ["point 1", "point 2"],
    "fresh_example": "example grounded in RAG or user context",
    "boundary": "what not to overtrust",
    "closing_rule": "one memorable criterion"
  },
  "final_answer": "3-5 natural Korean sentences only"
}
```

Purpose:

- Keep the model-driven structure without paying 3-4 sequential LLM calls.
- Make the LLM expose enough internal structure for deterministic verification.
- Let RAG influence angle/example/advice, not just append a citation sentence.
- Still return only `final_answer` to the user.

### 4.2 Runtime Intent Mapping

The existing code has 10 specific intent classes. They must map into the canonical taxonomy instead of coexisting as a separate schema.

| Current code intent | Canonical taxonomy mapping | Runtime primary |
| --- | --- | --- |
| `ai_energy_use` | `topic_domain=AI 원리`, `user_need=설명`, `must_include=데이터센터/GPU/냉각` | `principle_question` |
| `professional_cost_barrier` | `constraint_type=비용`, `user_need=저비용 대안` | `cost_barrier` |
| `isolation_dependency` | `emotion_state=외로움`, `constraint_type=주변 사람 부재` | `emotional_support` |
| `emotional_validation` | `emotion_state=불안/기대/외로움` | `emotional_support` |
| `particle_prediction` | `topic_domain=AI 원리`, `answer_shape=쉬운 예시` | `principle_question` |
| `noun_prediction` | `topic_domain=AI 원리`, `answer_shape=쉬운 예시` | `principle_question` |
| `attention_mechanism` | `topic_domain=AI 원리`, `user_need=작동 방식` | `principle_question` |
| `transformer_authors` | `topic_domain=AI 역사/출처`, `user_need=사실 확인` | `factual_curiosity` |
| `ai_error_mechanism` | `topic_domain=AI 원리`, `risk_level=medium if decision-impacting` | `principle_question` |
| `transformer_ml_hierarchy` | `topic_domain=AI 개념 구분`, `answer_shape=비교 설명` | `principle_question` |
| `general_principle` | `topic_domain=AI 원리`, `user_need=기초 설명` | `principle_question` |

V16 must implement this mapping as data, not more ad hoc branches.

### 4.3 Verifier

Checks after the single structured call:

- Directly answers user question.
- Uses selected RAG if RAG synthesis says usable.
- Does not use unsupported RAG.
- Has empathy when emotional.
- Does not contradict user constraint.
- Meets latency and length budget.
- Avoids known downvoted pattern.
- Does not let plan fields leak into final answer.

Verifier can be hybrid:

- deterministic checks for safety and latency
- small LLM judge only when ambiguity is high
- no LLM judge on fast low-risk paths unless needed

LLM judge trigger examples:

- deterministic checks disagree
- selected RAG is high value but final answer appears weakly grounded
- high-risk topic with low confidence
- repeated downvote cluster has no deterministic policy yet

LLM judge must not be part of the default happy path.

### 4.4 Fast-Template Retirement Policy

Fast-template is a temporary latency fallback, not the target answer engine.

Retirement rule:

- No new broad fast-template branches.
- Existing fast-template paths may remain only while structured generation proves equal or better latency and quality.
- A fast-template branch can be removed when:
  - corresponding structured packet tests pass,
  - max corpus/adversarial guard passes,
  - latency guard stays within budget,
  - no increase in downvote-pattern failures.

## 5. Latency Budget

Target budgets:

| Path | Target |
| --- | --- |
| Fast fallback, no RAG | < 300ms server-side |
| Fast path with RAG timeout | < 600ms server-side |
| Normal model answer | < 4s server-side |
| Retry path | avoid unless quality-critical |
| LLM judge | off by default, only ambiguous/high-risk |

Hard constraint:

- The default answer path must not exceed one LLM call.
- Any second LLM call requires explicit reason in usage metadata.
- Sequential A/B/C/D LLM calls are rejected for production runtime.

Current deployed guard:

- fast RAG timeout must stay <= 450ms in guard simulation
- fast-template must call LLM 0 times
- RAG patch path must call LLM <= 1 time

## 6. Rollout Plan

### v16: Deterministic Taxonomy Mapper + Single-Call Packet Prompt

Goal:

- Add one internal taxonomy/runtime intent mapper based on the Digital Twin Robustness Plan.
- Add a single-call structured answer packet prompt behind an environment flag.
- Keep existing rules as fallback and verifier.
- Do not remove current safety logic yet.

Acceptance:

- Existing max guard still passes.
- Unit tests cover emotional, cost, energy, principle, practical, and curiosity cases.
- No latency increase over v15/current guard.
- No additional LLM call on default path.
- Current 10 code intent classes map to canonical taxonomy fields.

### v17: RAG Synthesis Inside Single-Call Packet

Goal:

- Convert selected evidence into `fresh_angle`, `example_seed`, and `reader_relevance` inside the same LLM call.
- Stop treating RAG as only a sentence to append.

Acceptance:

- If RAG usable, final answer changes at least one of: angle, example, practical advice.
- If RAG weak, skip without delay.
- `evidence_used` means actual semantic use, not just selected.
- RAG retrieval + generation remains within latency guard.

### v18: Plan-Aware Verification, Not Separate Plan Call

Goal:

- Verify the `answer_plan` included in the single-call packet against `final_answer`.
- Do not introduce a separate plan-generation call unless a later benchmark proves it is worth the latency.

Acceptance:

- No cold/robotic plan labels leak into final answer.
- Answer variety increases across similar questions.
- Guard catches plan-answer mismatch.
- LLM call count remains 1 on happy path.

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

Rule escalation policy:

- Case-specific rule addition requires a failure taxonomy label.
- If the failure is not safety-critical, prefer corpus/scenario generation plus verifier metric over a new keyword branch.
- If a rule is added, it must include a retirement condition or justification for being permanent safety policy.

## 7.1 Governance And Approval Path

This plan changes answer-generation architecture, so approval is not a pure Codex implementation decision.

Roles:

| Role | Responsibility |
| --- | --- |
| Codex | implementation, tests, latency guard, local verification |
| Claude or equivalent strategy reviewer | architecture critique and product coherence review when available |
| Red Team Agent | adversarial review of answer quality and failure modes |
| QA Agent | final customer-facing readiness checks if the flow changes user-visible behavior |
| CEO/President | approve rollout if red-team resources are unavailable or if reviewers disagree |

Rollout gate:

- v16-v19 code changes require local tests and max guard.
- If Claude/Copilot/Gemini resources are unavailable, record `resource_gap_logged + local_guard_clear`; do not label it `red_team_clear`.
- If a release materially changes user-visible answer behavior, run at least one independent LLM critique when quota recovers.
- `Avoid adding more case-specific rules unless safety-critical` is enforced by Codex during implementation and audited by Red Team/QA when available.

## 8. Red-Team Questions For External LLM

Ask external LLM to evaluate:

1. Does this plan actually move away from rule-based FAQ behavior?
2. Is the proposed intent/context layer too complex or still too rule-like?
3. How should RAG synthesis influence answer planning without increasing latency too much?
4. What failure modes remain if rules are only safety rails?
5. What minimal v16 implementation would prove the architecture works?
6. What should be measured to detect whether answers are genuinely more creative?
7. Where could this plan create hallucination or over-personalized coaching risk?
8. Is the single-call packet schema sufficient, or should fields be removed to reduce prompt overhead?
9. Does the taxonomy mapping correctly subordinate this plan to the Digital Twin Robustness Plan?

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
- `0210202 docs: outline edu ai coach answer architecture`

Current known resource gap:

- Claude CLI session limit until 2026-06-27 21:30 KST.
- Copilot CLI quota 0.
- Gemini red-team excluded until configured and credit restored.

## 10. Decision Needed

Before more code changes, decide:

- Proceed with v16 deterministic taxonomy mapper + single-call packet prompt first.
- Or revise architecture based on external LLM critique.
- Avoid adding more case-specific rules unless they are safety-critical.

## 11. Diagnosis Resolution Log

Resolved issues from external diagnosis:

| Diagnosis issue | Resolution |
| --- | --- |
| Robustness Plan relationship missing | Added canonical ownership table and subordination rule. |
| Existing 10 intent classes vs new 6 intents unmapped | Added mapping table to canonical taxonomy and runtime primary intent. |
| 3-4 LLM call chain violates latency budget | Replaced sequential layers with one structured answer packet call. |
| RAG synthesis adds extra call latency | Moved RAG synthesis inside single-call packet. |
| Verifier trigger unclear | Added deterministic default and explicit LLM judge triggers. |
| Answer Plan separate call cost unclear | Changed v18 to plan-aware verification, not separate plan call. |
| Fast-template may remain forever | Added retirement policy and no-new-broad-fast-template rule. |
| v16 no-latency-increase criteria contradictory | v16 now uses deterministic mapper + one-call packet only. |

Open issues:

- Creativity scoring still needs concrete evaluator design.
- Governance path is now documented, but v16 implementation should still record actual reviewer/resource status.
- External Claude/Copilot review should be rerun when quota/session recovers.
