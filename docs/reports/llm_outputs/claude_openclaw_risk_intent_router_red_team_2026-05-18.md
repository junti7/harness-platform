Waiting for permission to write. Once granted, the full review will be saved to `docs/reports/llm_outputs/claude_openclaw_risk_intent_router_red_team_2026-05-18.md`.

---

## Red Team Output — Claude Pass

**Verdict: `conditional_approve`**

The layered design is the right structure and far better than flat single-LLM routing. Three failure modes, however, are not tail risks — they are predictable production failures that must be fixed before trusting this with real company operations.

---

### Top Findings (Severity Order)

**CRITICAL-1: Multi-step context chaining attack**

The high-risk trigger scan evaluates each message in isolation. A two-message sequence can trivially bypass it:

- Message 1: `"오늘 발행할 이슈 초안 있어?"` → no keyword hit → local LLM returns draft
- Message 2: `"그거 보내줘"` → "보내줘" alone doesn't hit publish keywords → Haiku routes it as a simple delivery command

Message 2 is a Slack broadcast instruction disguised as a follow-up. The scan never sees the context that makes it dangerous.

**Fix:** Layer 2 must scan a rolling window of the last N messages (minimum 3), not single messages.

---

**CRITICAL-2: Preflight gate is classification theater**

Layer 6 is described as "independently re-check." But if it uses the same keyword list or the same model as Layer 2, a first-pass misclassification survives identically. There is no independence — only the appearance of a second check.

**Fix:** Layer 6 must derive risk from an action-type registry (every bridge command mapped to `read_only | mutates_local | publishes | capital`), evaluated against the proposed *action*, not the original message. The action type registry is deterministic, not LLM-based.

---

**CRITICAL-3: Session state is solved for arithmetic only**

The architecture says local LLM "must preserve session history" but does not specify the session unit, storage, retention limit, or how history is injected into LLM calls. The original failure (arithmetic follow-up context loss) was patched as a special case. Every multi-turn exchange through any LLM route has the same structural problem.

**Fix:** Implement a session store keyed by Slack `thread_ts`. Inject last N turns into every LLM call. Define the token cap. This must exist before any LLM route handles multi-turn conversation.

---

**HIGH-1: Local LLM draft → production output enforcement gap**

The policy says local LLM outputs cannot publish or represent clearances. But there is no machine-readable enforcement. An operator under time pressure copies a local LLM draft directly to a subscriber channel. The architecture prohibits this but does not prevent it.

**Fix:** Tag every local LLM response with `source: local_llm, status: unreviewed_draft`. Any downstream bridge/delivery component must reject or hold tagged outputs for publish-type actions.

---

**HIGH-2: Korean semantic bypass of keyword trigger scan**

Korean high-risk intent can be expressed with no explicit noun: `"그거 올려도 돼?"`, `"저번에 말한 거 해줘"`, `"이거 나가면 안 돼?"`. A keyword scan built on `발행`, `유료`, `결제` misses all of these.

**Fix:** Demonstrative pronouns + action verbs (`그거/이거/저거` + `올려/보내/해줘`) must either route to Haiku for classification or default-escalate unless the prior context is deterministically safe.

---

**HIGH-3: Haiku confidence threshold is undefined**

"Low confidence" and "multiple intents conflict" are undefined. Without empirical calibration against real Harness Slack messages, the threshold will be arbitrary and either over-escalates (cost) or under-escalates (risk).

**Fix:** Before production, run 50+ real message samples through Haiku, record confidence distributions, set the threshold from that data, store it in config.

---

### What Must Never Be Delegated to Local LLMs

| Action | Reason |
|--------|--------|
| Any customer-channel output | No `qa_clear` mechanism; hallucination risk |
| Capital action records | Irreversible; requires `capital_action_approve` gate |
| Legal/compliance assertions | Confident false statements; no regulatory knowledge |
| Red Team / QA clearances | Requires cross-LLM independence — not self-review |
| Any `approval_type` record | All canonical approvals require human or Sonnet-level confirmation |
| Slack broadcast to subscriber channels | External-facing; wrong output = subscriber embarrassment or legal exposure |
| External API / webhook calls | Irreversible; local LLM lacks external system state |
| File mutations in production paths | Session context loss means local LLM may have incomplete file state |
| Price or tier changes | Requires pre-mortem and legal review per CLAUDE.md |

---

### Required Changes Before Production Trust (Blocking → High → Medium)

1. **Rolling risk window** — Layer 2 scans last 3+ messages, not single message. *Blocking.*
2. **Action-type registry in preflight** — Layer 6 derives risk from bridge command type, not from re-classifying the message. *Blocking.*
3. **Session state store** — All LLM routes receive injected session history keyed by `thread_ts`. *Blocking.*
4. **Local LLM output tagging with downstream enforcement** — Machine-readable draft tag + bridge rejection for publish-type actions on tagged output. *Blocking.*
5. **Korean demonstrative + action verb escalation** — Add to Layer 2 trigger patterns. *High.*
6. **Haiku threshold calibration** — Empirical, stored in config, documented. *High.*
7. **Prompt injection sanitization** — Wrap Slack message content in untrusted-input delimiter before any LLM call. *Medium.*
8. **Failure memory review cadence** — Weekly ops review; automatic promotion to Layer 1 rule when pattern appears ≥3 times. *Medium.*

---

### Residual Risks (After Fixes)

- Novel multi-step attack patterns will emerge; the failure memory loop is slow by design.
- Haiku model updates will shift confidence distributions; threshold requires periodic recalibration.
- Direct CLI bridge calls by operators bypass all router safety entirely — out of scope for this architecture but worth documenting.
- Cost overrun if ambiguous message volume spikes Sonnet usage; `DAILY_COST_LIMIT_USD` enforcement must be wired at the router layer before Sonnet dispatch.

---

**Note on Red Team completeness:** This is Claude's single-model pass. Per CLAUDE.md section 5, `red_team_clear` requires at minimum two different LLMs. A Gemini or GPT reasoning second pass is required before this design can receive `red_team_clear` and move to production deployment.
