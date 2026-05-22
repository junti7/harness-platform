# OpenClaw Risk/Intent Router Red-Team Review

Date: 2026-05-18
Scope: Slack message risk/intent routing architecture for OpenClaw and Harness operations.

## Review Inputs

- Request: `docs/reviews/red_team/OPENCLAW_RISK_INTENT_ROUTER_REQUEST_2026-05-18.md`
- Claude output: `docs/reports/llm_outputs/claude_openclaw_risk_intent_router_red_team_2026-05-18.md`
- Gemini output: `docs/reports/llm_outputs/gemini_openclaw_risk_intent_router_red_team_2026-05-18.md`
- Codex review: this memo

## Votes

| Reviewer | Verdict | Notes |
| --- | --- | --- |
| Claude | `conditional_approve` | Blocks production trust until rolling context risk scan, action-type preflight, session store, and local-output tagging are implemented. |
| Gemini | `conditional_approve` | Blocks production trust until high-risk trigger semantics, independent deterministic preflight, confidence thresholds, and human approval workflows are explicit. |
| Codex | `conditional_approve` | Architecture direction is correct, but current design must not be treated as `red_team_clear` for production without enforceable gates. |

Result: **2-of-3+ conditional approval, not full approval.**

This is **not** `red_team_clear` for production. It is permission to proceed with implementation of the required safeguards.

## Material Findings

### 1. Single-message classification is unsafe

The most dangerous failure mode is multi-turn context bypass.

Example:

- Turn 1: `오늘 발행할 초안 있어?`
- Turn 2: `그거 보내줘`

Turn 2 may look harmless in isolation, but in context it can become an external publication or Slack broadcast. Risk scanning must include a rolling context window, not only the latest message.

Required change:

- Scan at least the latest user message plus the last 3-5 turns.
- Treat demonstrative Korean references such as `그거`, `이거`, `저거`, `아까 말한 거`, `그대로` as context-dependent.
- If the referenced object is not deterministically safe, escalate.

### 2. Preflight must inspect proposed action, not original text

Both Claude and Gemini flagged the same issue: a second keyword scan is not an independent preflight. It only repeats the original failure.

Required change:

- Add a deterministic action registry.
- Every executable route/bridge command/tool must declare:
  - `risk_level`
  - `action_type`
  - `mutates_state`
  - `external_effect`
  - `requires_approval`
  - `allowed_models`
  - `required_gates`

Preflight must evaluate the proposed action from this registry before execution.

### 3. Local LLM outputs need machine-readable tainting

Policy saying "local LLM cannot publish" is insufficient. The system must enforce it.

Required change:

- Any output from Ollama/Gemma/Qwen must carry metadata such as `source_model_tier=local`, `status=unreviewed_draft`.
- Publish, Slack broadcast, customer-facing, approval-record, and mutation routes must reject local-tainted artifacts unless promoted through required gates.

### 4. Confidence thresholds are currently undefined

If Haiku or another cheap router says "low-risk" with no calibrated confidence semantics, the label is not trustworthy.

Required change:

- Define allowed router outputs as structured JSON.
- Include `intent`, `risk_level`, `confidence`, `evidence_terms`, `ambiguity_flags`.
- If confidence is below threshold or conflicts exist, route to clarification or premium/human gate.
- Calibrate on real Harness Slack samples, not invented examples.

### 5. Human approval boundaries must be explicit

High-risk actions need auditable human gates, not just LLM escalation.

Mandatory human gate categories:

- external publication
- paid offer, pricing, refund, subscription terms
- capital action
- legal/regulatory claim
- customer-facing factual artifact
- destructive file/database mutation
- canonical approval recording
- CEO/VP decision card finalization

## What Must Never Be Delegated To Local LLMs

- External customer/subscriber communication
- Legal, regulatory, investment, or capital-action judgment
- Approval semantics such as `red_team_clear`, `legal_review_approve`, `qa_clear`, `capital_action_approve`
- Production file/database mutation
- Slack broadcast to official channels
- Pricing, refund, paid tier, or paid offer changes
- Final executive report or decision card
- Any output that claims source-backed factual certainty without QA

## Required Before Production Trust

1. Implement rolling context risk scan.
2. Implement deterministic action registry and preflight gate.
3. Add local LLM output tainting and downstream enforcement.
4. Define structured router schema and confidence thresholds.
5. Add Korean context-dependent escalation patterns.
6. Add audit log fields: `intent`, `risk_level`, `route`, `model`, `confidence`, `gates_checked`, `cost_estimate`, `final_action`.
7. Add regression tests for multi-turn bypasses and high-risk Korean phrasing.

## Red-Team Decision

Decision: `conditional_approve`

Allowed next step:

- Implement the safeguards above.
- Do not mark the architecture as production-safe.
- Do not allow local LLM or cheap router output to trigger mutation, publication, paid, legal, approval, or executive decision flows without deterministic preflight and required gates.

Blocked claim:

- `red_team_clear` is not granted for production deployment.

Residual risk:

- Even after these changes, new ambiguous phrasing and prompt-injection patterns will appear. Failure memory and scheduled red-team review must remain active.
