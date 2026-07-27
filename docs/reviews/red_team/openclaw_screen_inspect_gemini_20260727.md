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

## Incremental bridge-selection review

After adding fallback selection for the Peekaboo bridge socket, Gemini reviewed the strengthened readiness gate.

Fix criteria reviewed:
- Exactly one selected bridge candidate.
- Reject `result.failure`.
- Require `result.success._0`.
- Require `hostKind` of `gui` or `onDemand`.
- Require `supportedOperations.captureScreen`.
- Require `permissionTags.captureScreen` to include `screenRecording`.

Follow-up verdict: `safety_review_clear`

## Incremental follow-up routing review

After the Discord request `다시 확인해` was blocked with
`screen_inspect_not_bound_to_routed_owner_request`, Gemini reviewed the follow-up
intent routing patch.

Initial findings:
- Raw prompt/context scanning could trust user-controlled `[assistant]` spoofing.
- Stringifying assistant content could trust quoted JSON text that only looked
  like a tool call.
- Fail-open stringify behavior was unsafe.

Fix applied:
- Do not parse raw `<conversation_context>` for follow-up trust.
- Trust only structured assistant `content[].type === "toolCall"` records whose
  `name` or `toolName` is exactly `harness_screen_inspect`.
- Trust only structured `toolResult` messages whose `toolName` is exactly
  `harness_screen_inspect`.
- Bare follow-ups and user-role marker injection fail closed.

Follow-up verdict: `red_team_clear`

Reviewer output excerpt:
> `red_team_clear`
>
> Eliminated Raw Prompt/String Spoofing: `trustedScreenInspectContext` completely
> ignores prompt text / stringified prompt blocks and strictly iterates over
> structured `messages` objects.
>
> Strict Message Schema Checks: It only pushes trust markers if role/toolName or
> structured assistant toolCall exactly names `harness_screen_inspect`.
