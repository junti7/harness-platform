# Copilot Review — VP AI Training Program

## Verdict
- conditional_block

## Findings
1. [high] Scope is carrying three products at once. `VP_AI_TRAINING_PROGRAM_DEVELOPMENT_PLAN.md` mixes VP beginner training, external parent-service preproductization, and internal operator shadowing in one structure. Long-term vision is coherent, but Phase 1 scope is too broad and can collapse into a document-heavy program.

2. [high] Practice-first is stated clearly, but not enforced strongly enough in the operating contract. The plan says 70% execution and “no practice-less lessons,” but it still leans on lesson/session/artifact/reflection structure without a strict weekly contract of one observable action, one proof artifact, and one pass/fail rubric tied to real tool use.

3. [high] The data model risks creating a second state machine beside the standalone app. The standalone app plan already defines case/device/tool-readiness/session control, while the VP plan adds `edu_training_*` objects without making canonical ownership of progression and readiness explicit.

4. [high] RAG usage is directionally right but operationally under-specified. The plan says to use Harness RAG aggressively, but training cards still need explicit lineage: evidence bundle ID, retrieval mode, safe-view confirmation, version stamp, fallback flag.

5. [high] The operator-mirror environment is conceptually correct but not yet safe enough to build against. “Read-mostly, low-risk, reversible” is not a sufficient contract without explicit mirrored data class, permissions, reset path, shadow-account design, and banned actions.

6. [medium] External-service reuse is plausible, but the reuse boundary is blurry. The strongest reusable asset is the beginner practice path, not the internal operator path, and the plan should partition those more clearly.

7. [medium] The selected-LLM/device matrix is too large for Phase 1. Supporting iPhone/Android/Windows/Mac and multiple LLM branches simultaneously will create maintenance overhead before product learning quality is stable.

8. [medium] Governance alignment is not fully clean. `CLAUDE.md` is aligned with AI education consulting, but `AGENTS.md` still foregrounds other top-level business identity and priority, which can blur ownership and success criteria.

## Required Changes Before Clear
1. Narrow Phase 1 to one executable slice: Week 0 + Week 1 + one mobile→PC/Mac handoff path + one primary LLM path.
2. Separate the curriculum into two tracks: customer-facing beginner practice and internal operator mirror.
3. Make practice-first non-negotiable in the schema: one concrete task, one proof artifact, one pass/fail rubric, one blocked-at-step field.
4. Choose one canonical state model by reusing standalone app case/device/tool-readiness primitives and adding only minimal training-specific metadata.
5. Add a training-material lineage contract for every RAG-backed lesson card.
6. Write an explicit operator-mirror spec before implementation.
7. Reduce the support matrix for the first cohort.
8. Resolve governance drift between `AGENTS.md` and `CLAUDE.md`.

## Residual Risks After Fix
1. VP-first learning data may still be too narrow to represent the broader parent customer base.
2. Device/browser fragmentation will remain expensive even after scope reduction.
3. RAG freshness and rights safety will remain ongoing operational work.
4. Operator shadowing can still pull the public curriculum upward in complexity unless guarded tightly.

