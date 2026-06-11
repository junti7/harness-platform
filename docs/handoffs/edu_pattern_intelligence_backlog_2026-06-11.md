# Edu Pattern Intelligence Backlog

Date: 2026-06-11
Source plan: `docs/handoffs/edu_pattern_intelligence_plan_2026-06-11.md`

## Phase 1. Data Backbone

1. Add `edu_pattern_facts` schema and persistence path.
2. Add extraction pipeline from `edu_case_turns`, `runtime/edu_pilot_runtime_events.jsonl`, and `data/edu_research/evidence_bank.json`.
3. Add PII scrubbing before `quote_text` persistence.
4. Split self-stated vs inferred demographic attributes and default low-confidence inferred fields to analysis-only.
5. Add complaint tagging fields:
   - `complaint_signal`
   - `complaint_type`
   - `dissatisfaction_severity`
6. Add operator review path to mark answer-failure cases.

## Phase 2. Pattern Builder

1. Create `scripts/build_edu_pattern_intelligence.py`.
2. Implement cluster building for:
   - pain clusters
   - desire clusters
   - complaint clusters
   - answer-failure clusters
3. Compute:
   - `pattern_score`
   - `monetization_signal_score`
   - `complaint_risk_score`
4. Add holdout/off-policy split to prevent self-reinforcing transcript loops after runtime injection.
5. Emit `data/edu_research/pattern_registry.json`.

## Phase 3. Review Gates

1. Create `scripts/fact_check_edu_patterns.py`.
2. Enforce thresholds:
   - minimum sample size by cohort
   - minimum distinct source count
   - counterevidence ratio cap
   - complaint recurrence check
3. Add Red Team review artifact generation.
4. Require `qa_clear`, `legal_review_approve`, and CEO/VP sign-off before runtime use.
5. Add TTL/expiry and revalidation rules for approved patterns.

## Phase 4. Runtime Reuse

1. Limit personalization inputs to user-explicitly-stated context only.
2. Prohibit inferred demographic runtime biasing.
3. Use approved patterns for:
   - opener framing
   - retrieval reranking
   - quick reply shaping
   - complaint recurrence prevention
4. Add `avoid_response_patterns` and `known_failure_modes` consumption in answer orchestration.
5. Add regression checks so complaint-prevention logic does not cause evasive or overly defensive answers.

## Phase 5. Measurement

1. Track complaint-rate by cluster.
2. Track repeated dissatisfaction on similar prompts.
3. Track satisfaction delta after pattern-based improvements.
4. Track false-pattern demotions and stale-pattern expiry.
5. Produce weekly top-cluster and top-complaint diff reports.

## Non-Negotiable Guards

- This system exists to improve preparedness and response quality, not to pre-judge users by stereotype.
- Complaint signals must be treated as high-priority quality failures, not as noise.
- Any runtime-shaping use is blocked until the stronger gate stack is implemented.
