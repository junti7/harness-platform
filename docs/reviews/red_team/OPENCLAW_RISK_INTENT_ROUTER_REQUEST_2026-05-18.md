# OpenClaw Risk/Intent Router Red-Team Request

Date: 2026-05-18
Scope: Proposed routing architecture for Slack -> OpenClaw -> Harness operations.

## Context

Recent Slack failures showed that routing ordinary follow-up messages through local LLMs with a strong Harness persona caused context loss and irrelevant answers.

Example failure:

- User: `1+1=?`
- Assistant: answered `2`, then added Harness Chief of Staff persona boilerplate.
- User: `거기에 3을 나누면?`
- Assistant: asked what number to divide, failing to use previous context.

Immediate patch:

- Simple arithmetic and arithmetic follow-up now bypass all LLMs through deterministic Python logic.
- Slack listener has been restarted in the actual runtime path.

However, arithmetic is only a smoke test. The real design question is whether Harness can safely classify Slack messages by risk and intent before choosing deterministic bridge, local LLM, Haiku router, Sonnet tool agent, or human gate.

## Proposed Architecture

Message flow:

1. Deterministic allowlist parser.
   - Handles exact or strongly patterned commands such as status, `/goal`, approval records, pipeline commands, arithmetic.
   - Zero LLM cost.
   - Only assigns low risk when matched with high confidence.

2. High-risk trigger scan.
   - Keywords or semantics involving publish, paid offer, pricing, refund, legal, capital action, investment, external claim, file mutation, deletion, Slack broadcast, CEO/VP decision, brand-risk output.
   - If triggered, route upward regardless of local model or Haiku suggestion.

3. Ambiguous natural-language command router.
   - Haiku or equivalent cheap router may map ambiguous messages to bridge commands.
   - Router has no execution authority.
   - If confidence is low or multiple intents conflict, escalate to clarification or Sonnet.

4. Local LLM route.
   - For low-risk short conversation, classification, dedup, cheap summarization, non-customer-facing drafts.
   - Must preserve session history.
   - Outputs are not allowed to publish, mutate files, spend money, approve decisions, or represent legal/QA/Red-Team clearances.

5. Premium LLM / tool route.
   - Sonnet or equivalent for file edits, code changes, executive synthesis, strategy, high-context reasoning, tool execution, external-facing artifacts.

6. Preflight gate.
   - Before execution, independently re-check whether the action mutates data, publishes externally, affects pricing/legal/capital/brand, or needs approval.
   - This catches first-pass classification mistakes.

7. Post-run audit and failure memory.
   - Record route, risk, model, cost, confidence, output, and failure pattern.
   - Add repeated failures to `OPENCLAW_FAILURE_MEMORY.md` or equivalent.

## Red-Team Questions

1. What is the strongest failure mode in this architecture?
2. Is rule-first + high-risk trigger + cheap router + preflight sufficient, or does it still allow dangerous low-risk misclassification?
3. What should be added before this is trusted for real company operations?
4. What should never be delegated to local LLMs?
5. Should this design be approved, conditionally approved, or blocked?

## Expected Output

Return:

- verdict: `approve`, `conditional_approve`, or `block`
- top findings ordered by severity
- required changes before production trust
- residual risks
