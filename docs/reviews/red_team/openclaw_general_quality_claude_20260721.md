# Claude Red Team — OpenClaw General Response Quality Rebuild

- Date: 2026-07-21
- Reviewer: Claude Sonnet CLI
- Review mode: independent, read-only
- Verdict: `red_team_block`

## Findings

1. The proposed architecture is a sound target, but its typed contract, normalized evidence, claim ledger, and delivery decision do not exist in the implementation.
2. `premium_tool_agent` output is treated as declared tool evidence and can pass without proving that the tool result is relevant to the requested subject.
3. Requests not recognized by the narrow Gmail and Korean analysis/recommendation patterns default to `direct`, including some current-fact questions.
4. Verification operates on one coarse evidence record for the entire answer. One supported claim can mask unsupported claims in the same response.
5. `partial` is a prose prefix, not a structured state that downstream delivery must preserve.
6. The release gates have no executable corpus, scorer, or shadow dashboard.
7. Existing generic-contract regression coverage is effectively limited to the Gmail evidence mismatch.

## Positive finding

The tool-call authorization/preflight path is fail-closed for registered state-changing tools. This existing control should be preserved while authorization metadata is consolidated.

## Required release conditions

- Fix tool-evidence and default-`direct` bypasses with old-code-failing tests.
- Implement structured `DeliveryDecision` so partial and abstain cannot be swallowed.
- Provide an executable corpus-backed release metric.
- Add a named rollback switch.
- Independently re-review the implementation diff and production shadow evidence.

The review does not clear future implementation. It confirms that the current production code remains blocked as a general evidence verifier.
