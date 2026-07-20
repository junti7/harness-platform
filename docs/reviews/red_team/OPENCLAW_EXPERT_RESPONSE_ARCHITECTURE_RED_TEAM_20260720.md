# Red Team Review: OpenClaw Expert Response Architecture

- Date: 2026-07-20
- Artifact reviewed: `docs/strategy/OPENCLAW_EXPERT_RESPONSE_ARCHITECTURE_20260720.md`
- Verdict: `red_team_block`
- Reason: required independent Claude review unavailable; original design also lacked mandatory enforcement controls.

## Review coverage

| Reviewer | Role | Result | Artifact / evidence |
| --- | --- | --- | --- |
| Codex | architecture evidence review | findings accepted into revised strategy | inspected `adapters/content/openclaw_agent.py`, `scripts/openclaw_codex_bridge.py`, and `tests/test_openclaw_agent.py` |
| GitHub Copilot CLI | independent adversarial review | `BLOCK` | CLI session `c44da2f2-6034-47d9-8e5a-aa73ac18484e`; prompt and output summarized below |
| Claude CLI | required independent reviewer | unavailable | `claude -p --bare --model sonnet ...` returned `Not logged in · Please run /login` |

Claude + Copilot pair is required for this architecture/code-change class under `AGENTS.md`. Copilot alone does not clear the gate.

## Code evidence

- System guidance requires email search followed by `gmail_get` body retrieval before a summary.
- `_try_gmail_summary_response()` instead calls only `_gmail_search_json()` and formats `date | from | subject`.
- `run()` executes this deterministic route before the tool-agent path.
- Bridge supports body retrieval through `gmail-get`, so capability exists but fast-path does not use it.

## Copilot prompt

Independent adversarial review of proposed all-intent architecture: request contract; evidence planner; deterministic claim limits; evidence freshness/coverage; reasoning; verifier; partial-result delivery; observability and golden tests. Specific known defect: Gmail summary route returns headers after search and bypasses body retrieval.

## Copilot finding summary

Verdict `BLOCK`.

1. Route priority can bypass reasoning and verifier.
2. A summary contract can still complete with metadata-only evidence.
3. Partial results can look final.
4. Verifier can fail open.
5. Privacy minimization and evidence sufficiency can conflict without explicit controls.
6. Freshness metadata alone does not block stale answers.

Required acceptance controls: hard evidence gate for `summary|analysis|recommendation`; typed stage schema; deterministic claim whitelist; fail-closed verifier; runtime and regression assertions; contract/evidence mismatch and partial-result SLOs.

## Codex findings

1. Existing Gmail system prompt and fast-path behavior contradict one another. Policy text alone cannot prevent bypass.
2. `newer_than:1d` is rolling time, not a Korea-calendar meaning of `today`.
3. Existing test protects current faulty behavior by asserting deterministic mail route and no model call; test contract must be replaced, not merely supplemented.
4. Body content is untrusted data. It must be treated as evidence, never as tool instructions.
5. Slack's 300-second listener ceiling requires bounded retrieval and explicit partial-result delivery, not hidden timeouts.

## Release condition

Re-review after implementation evidence includes:

- contract/evidence runtime assertion;
- Gmail lookup vs brief tests;
- failure and prompt-injection tests;
- shadow-run measurements;
- successful independent Claude and Copilot reviews.

Until then, no `red_team_clear` and no production rollout approval.

## Implementation follow-up

The first reference adapter is implemented locally but remains unapproved for production rollout.

- Gmail requests now split into `gmail_lookup` (explicit metadata requests) and `gmail_brief` (content/summary requests).
- `gmail_brief` fetches selected bodies concurrently; any missing body produces an explicit partial result instead of a headers-only summary.
- Asia/Seoul calendar boundaries are used for `today` and `yesterday` Gmail queries.
- Gmail body excerpts are excluded from persisted conversation history.
- Tests passed: `67` OpenClaw agent tests and `5` route-audit summary tests.

Actual-diff Copilot re-review did not return a verdict after file inspection, so it is inconclusive and does not replace the required independent review. Claude CLI remains unavailable because it is not logged in. Verdict remains `red_team_block`.

## Authenticated re-review and remediation

Claude CLI authentication was restored and independent Claude + Copilot reviews ran on 2026-07-20. Both reviewers returned `red_team_residual_risk`, not a clear, because the Slack production path had not yet been exercised.

- Claude artifact: `docs/reviews/red_team/openclaw_gmail_brief_claude_20260720.md`
- Copilot artifact: `docs/reviews/red_team/openclaw_gmail_brief_copilot_20260720.md`
- Copilot KST-boundary and raw-error findings were remediated before deployment: KST requests now filter returned message timestamps locally; raw bridge errors are normalized out of the user response.
- Regression evidence after remediation: 69 OpenClaw agent tests, 5 route-audit tests, and a configured Gmail runtime KST brief check passed.

Verdict remains `red_team_residual_risk` until targeted Mac Mini Slack listener deployment and actual DM-path verification complete.
