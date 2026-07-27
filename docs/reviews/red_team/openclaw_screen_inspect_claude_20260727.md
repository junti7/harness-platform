# Claude Red Team Review — OpenClaw screen inspect fail-fast

Date: 2026-07-27

Model: `claude-sonnet-4-6` via `agy`

Status: `red_team_clear`

Summary:
- Owner gating passes: routing requires `currentSenderIsOwner()` and `shouldEnforceScreenInspect()`.
- Direct unrouted calls cannot mint an execution token.
- Peekaboo shell bypass is blocked during screen-inspection routing.
- All Peekaboo stages have explicit timeouts: bridge status 3 seconds, permissions 3 seconds, screen inspection 15 seconds.
- The implementation is read-only and does not introduce click, type, login, cart, order, purchase, payment, or form-submit actions.

Reviewer output excerpt:
> `red_team_clear`
>
> All four focus areas pass. The implementation is a faithful port of the `harness_browser_open` two-phase gating pattern with appropriate read-only constraints, bounded timeouts at every async stage, and shell/Peekaboo bypass blocking tested with a concrete evasion case. No click, type, buy, or data-leak vectors introduced.

Non-blocking note:
- Real screen inspection still requires the OpenClaw GUI bridge socket and macOS Screen Recording/Accessibility permissions to be present at runtime.

## Incremental bridge-selection review

After adding fallback selection for the Peekaboo bridge socket, Claude initially returned `red_team_block` because a simple `success` key check weakened the prior GUI-readiness assertion.

Fix applied:
- Validate exactly one candidate for the selected socket.
- Reject any `result.failure`.
- Require `result.success._0`.
- Require `hostKind` to be `gui` or `onDemand`.
- Require `supportedOperations` to include `captureScreen`.
- Require `permissionTags.captureScreen` to include `screenRecording`.

Follow-up verdict: `red_team_clear`

Reviewer output excerpt:
> All stated validation criteria are correctly and defensively implemented. No bypass vectors or logic gaps found in the incremental diff.

## Incremental follow-up routing review

After the Discord request `다시 확인해` was blocked with
`screen_inspect_not_bound_to_routed_owner_request`, Claude reviewed the final
follow-up intent routing patch.

Fix criteria reviewed:
- Raw prompt role spoofing must not create trusted screen-inspection context.
- Follow-up routing must fail closed when there is no prior structured
  `harness_screen_inspect` tool call/result.
- Assistant text that merely quotes `{"name":"harness_screen_inspect"}` must not
  be treated as a tool call.
- Stringify or malformed content must not grant routing.

Follow-up verdict: `red_team_clear`

Reviewer output excerpt:
> `red_team_clear`
>
> All three previously raised concerns are addressed.
>
> `trustedScreenInspectContext` now ignores `prompt` entirely and only walks the
> structured `messages[]` array.
>
> Now requires `item.type === "toolCall"` structurally; the `type:"text"` test
> case explicitly asserts `false`.

## Incremental trajectory fallback review

The first live replay after the structured-message follow-up patch still
returned `screen_inspect_not_bound_to_routed_owner_request` because the
`before_prompt_build` hook did not receive historical `messages[]` for that
OpenClaw route. A trajectory fallback was added and reviewed.

Fix criteria reviewed:
- No raw prompt or raw JSONL regex should establish trust.
- Session ID and resolved path must prevent traversal.
- File reads must be bounded and fail closed.
- Follow-up trust must require structured trajectory `tool.call` plus
  `tool.result` records for `harness_screen_inspect`.
- Assistant text that merely quotes matching strings must remain false.

Follow-up verdict: `red_team_clear`

Reviewer output excerpt:
> `red_team_clear`
>
> Only `type === "tool.call"` and `type === "tool.result"` events with
> `data.name === "harness_screen_inspect"` are accepted. `model.completed` /
> `assistant` texts are never consulted.
