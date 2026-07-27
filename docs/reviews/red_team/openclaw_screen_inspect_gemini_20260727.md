# Gemini Red Team Review — OpenClaw screen inspect fail-fast

Date: 2026-07-27

Model: `gemini-3.6-flash-low` via `agy`

Status: `safety_review_clear`

Summary:
- Owner-gated screen inspection is routed through `before_prompt_build` and execution-token binding.
- Peekaboo shell calls are blocked during screen-inspection routing.
- Bridge status and permission checks are bounded at 3 seconds; screen inspection is bounded at 15 seconds.
- The change does not introduce GUI click/type/form/payment actions.
- High-impact browser actions remain excluded.

Reviewer output excerpt:
> `safety_review_clear`
>
> Owner-Gated Screen Inspection: `before_prompt_build` strictly checks `currentSenderIsOwner(event.prompt, context)` along with `shouldEnforceScreenInspect(event.prompt)` before attaching the system instruction and marking the run as active for `screenInspect`.
>
> Peekaboo Shell Blocking: When screen-inspect routing is active, any attempt to invoke shell tools or explicit Peekaboo shell invocations is intercepted and blocked.
>
> Timeout and Fail-Fast Behavior: Status check uses `timeoutMs: 3_000`, permissions check uses `timeoutMs: 3_000`, and inspection uses `timeoutMs: 15_000`.
