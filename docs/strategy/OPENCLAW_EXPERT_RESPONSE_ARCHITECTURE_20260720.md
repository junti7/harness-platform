# OpenClaw Expert Response Architecture

- Date: 2026-07-20
- Status: baseline delivery guard implemented; deeper evidence verifier remains incremental work
- Scope: all Slack DM responses. This is not a Gmail-only patch.

## Outcome

OpenClaw must answer every request as an accountable operator: determine what the user asked, collect evidence adequate for that answer, state the answer first, distinguish facts from inference, expose uncertainty, and never make an unauthorized change.

## Non-negotiable invariant

`answer_contract` determines the minimum evidence before delivery. A route may not claim more than its evidence supports.

| Answer contract | Minimum evidence | Delivery rule |
| --- | --- | --- |
| `lookup` | authoritative metadata or record | deterministic response allowed |
| `summary` | primary content/body for every included item, or explicit exclusion | block final summary when coverage is incomplete |
| `analysis` | primary evidence plus dated context | evidence and inference separated |
| `recommendation` | analysis evidence, uncertainty, risks, and approval boundary | no external/state-changing action |
| `action` | explicit authorization plus preflight success | execute only through existing action gate |

Example: Gmail headers support `lookup`. They do not support `summary`. A request containing `내용`, `요약`, `핵심`, `중요`, `검토`, `왜`, or `무엇을 해야` requires `summary` or higher; it must fetch selected message bodies with `gmail_get`.

## Required response pipeline

1. **Request contract**: classify intent, answer contract, requester, time range, action risk, and expected response shape. Ambiguous requests ask one targeted question only when the ambiguity materially changes evidence or authority.
2. **Evidence plan**: choose minimum authoritative sources, required fields, freshness threshold, coverage target, and privacy budget before fetching.
3. **Evidence collection**: retrieve only approved read-only sources. Preserve source IDs, timestamps, fetch outcome, and omitted-item reason. Do not put full private bodies in route audit logs or session persistence.
4. **Reasoning and drafting**: answer first; then supporting evidence, uncertainty, and next action. Group duplicates/alerts only after inspecting enough content to establish grouping. Never invent contents from sender or subject.
5. **Independent verifier**: validate contract-to-evidence coverage, claim provenance, freshness, instruction compliance, privacy, authorization, and output usefulness.
6. **Delivery**: verifier pass delivers. Verifier fail returns a mandatory partial-result template or blocks. It must never silently degrade a requested summary into a header list.

## Route policy

Deterministic routes remain for arithmetic, status lookups, and other fully evidenced facts. They must declare both `answer_contract` and allowed claim types. A router cannot pre-empt the evidence plan merely because a keyword matched.

`deterministic_gmail_summary` is replaced conceptually by two contracts:

- `gmail_lookup`: search metadata; allowed only for explicit list/title/sender/count requests.
- `gmail_brief`: search, select, body-fetch in parallel with bounded timeout, deduplicate/classify, draft, and verify. Applies to content/summary/importance/action requests.

Any body-fetch failure lowers coverage. If coverage falls below contract threshold, deliver `partial_result`, naming missing evidence, decision impact, and a safe retry condition.

## Gmail quality policy

- Interpret `today` using Asia/Seoul calendar boundaries, not rolling `newer_than:1d`.
- Search more candidates than final display count, then select by unreadness, sender trust, directness, deadline, and work relevance.
- Fetch bodies only for selected messages; cap item count and body length.
- Consolidate mechanically similar alerts only after body/link inspection. Keep individual source links available.
- Output: `immediate action`, `decision/useful signal`, `reference`, `uncertainty`. No false urgency.

## Fail-closed controls

- `summary`, `analysis`, and `recommendation` cannot be marked final without verifier success.
- Contract/evidence mismatch is a runtime assertion and blocks normal delivery.
- Verifier failure cannot be converted to a normal response by a fallback route.
- A partial result must state: evidence unavailable, affected conclusion, and next safe action.
- State-changing requests keep existing authorization/preflight gates; better prose never grants authority.

## Measurement and release gates

| Metric | Initial release gate |
| --- | --- |
| contract/evidence mismatch | 0 in test suite; alert on any production event |
| summary requests with required body evidence | 100% |
| verifier failure sent as normal final answer | 0% |
| partial-result template completeness | 100% |
| sampled claim-to-evidence match | >=99% |
| P95 Gmail brief latency | target <=30s; partial-result path before Slack 300s ceiling |

## Implementation sequence

1. Add typed `RequestContract`, `EvidenceSet`, `VerificationResult`, and `DeliveryResult`; do not add another keyword exception.
2. Move existing fast-paths behind contract declaration and allowed-claim assertions.
3. Implement Gmail lookup/brief as first reference adapter, including KST time boundaries and bounded parallel body retrieval.
4. Add verifier plus fail-closed delivery adapter.
5. Add capability-contract tests, fixture-based golden conversations, fault injection, and sampled production audit.
6. Shadow-run against read-only Slack requests; compare contract, evidence coverage, latency, and usefulness before enabling delivery.

## Required regression suite

- Exact lookup request: no unnecessary body retrieval.
- Broad summary request: body retrieval required; headers-only final response blocked.
- Mixed promotional, alert, and direct operational mail: classify and group without hiding direct action.
- Partial body failure: required partial-result wording; no invented summary.
- Stale web/market answer: freshness mismatch blocks definitive present-tense claim.
- Ambiguous and high-risk action requests: authority gate remains intact.
- Prompt injection inside retrieved content: content cannot change tools, policy, or authorization.

## Rollout decision

Do not ship yet. Red Team clearance is missing because Claude review could not run, and Copilot identified missing hard gates in the original proposal. Implement the controls above, then rerun Claude + Copilot independent review with test evidence.

## 2026-07-21 implementation baseline

The shared delivery path (`_finalize_response`) now applies a route-independent
quality guard to every OpenClaw response:

- prompts require answer-first delivery; briefing, summary, analysis, decision,
  review, and report requests use a conclusion-first structure;
- secret-shaped strings are redacted before delivery;
- accidental email/CSS rendering fragments are blocked unless the user explicitly
  requested code or markup;
- the guard never invents evidence. It only redacts unsafe output or adds a
  structural `결론:` label where the response did not already lead naturally;
- Gmail remains the first reference adapter with its own evidence/coverage gate.

`run()` now also emits a `contract_verification` audit record for each delivery,
using `RequestContract`, `EvidenceSet`, and `VerificationResult`. A Gmail
summary without message-body evidence is fail-closed; incomplete body coverage
uses the existing explicit partial-result response.

This is not yet the full typed all-intent verifier proposed above. In
particular, `RequestContract`, `EvidenceSet`, per-claim provenance, and
fail-closed evidence coverage for every tool route remain follow-up work.
