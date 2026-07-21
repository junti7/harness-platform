# OpenClaw General Response Quality Rebuild

- Date: 2026-07-21
- Scope: every OpenClaw Slack DM response
- Status: proposed; production rollout blocked until implementation, evaluation, and Red Team clear
- Owner: CEO Chief of Staff / OpenClaw

## Decision

OpenClaw must stop treating route identity, prompt wording, or model confidence as evidence. The current shared guard improves formatting and catches a few known failures, but it cannot prove that an answer addresses the requested subject with relevant, current, sufficient evidence.

The replacement is one domain-independent pipeline:

```text
request
  -> typed answer contract
  -> evidence plan
  -> evidence collection
  -> evidence normalization
  -> draft with claim ledger
  -> independent deterministic verification
  -> deliver | partial | abstain
```

Domain adapters may collect evidence. They may not decide whether the final answer is supported. Adding a new keyword route for each failed question is not an acceptable quality fix.

## Confirmed defects in the current implementation

1. `RequestContract` describes only `kind` and a Gmail-oriented primary-evidence flag. It does not identify the requested subject, time scope, required dimensions, authority, or response completeness.
2. `EvidenceSet` describes only `source` and `coverage`. It cannot prove relevance to the requested subject, freshness, authority, or which claims it supports.
3. `_evidence_for_route()` infers evidence from the route name. Any deterministic or bridge route becomes `runtime_record/complete`, even when the returned runtime record is irrelevant to the question.
4. Verification occurs after drafting. The model can draft unsupported claims before an evidence plan exists.
5. Verification checks the answer category, not individual factual claims. Broad claims such as “all systems normal” can pass without evidence for every named subsystem.
6. Prompt-injected context is untyped prose. The model can mix generic status, stale files, and domain-specific data without provenance boundaries.
7. The current “hypothesis” prefix changes presentation but does not prevent unsupported factual statements inside the response.

## Universal answer contract

Every request receives a typed contract before routing:

```json
{
  "task_type": "transform|lookup|status|summary|analysis|recommendation|action|creative",
  "subjects": [{"id": "canonical subject", "aliases": []}],
  "requested_dimensions": ["state", "cause", "risk", "next_action"],
  "time_scope": {"kind": "current|historical|timeless", "as_of": null},
  "required_evidence": {
    "minimum_authority": "primary|authoritative_runtime|trusted_secondary|none",
    "freshness_seconds": null,
    "coverage": "complete|representative|best_effort"
  },
  "action_boundary": "read_only|draft_only|approval_required|authorized",
  "response_shape": "direct|brief|report|artifact",
  "ambiguities": []
}
```

Rules:

- `transform` and `creative` requests may require no external evidence unless they introduce factual claims.
- `lookup`, `status`, `summary`, `analysis`, and `recommendation` require evidence appropriate to their contract.
- A material ambiguity asks one targeted question or returns an explicit bounded interpretation.
- The model may not silently broaden the subject, time range, or requested dimensions.

## Evidence contract

Every collected item is normalized before it reaches the drafting model:

```json
{
  "evidence_id": "stable id",
  "subject_ids": ["canonical subject"],
  "dimensions": ["state"],
  "source_type": "runtime|database|api|file|web|user_content",
  "authority": "authoritative_runtime|primary|secondary|unverified",
  "observed_at": "timestamp",
  "valid_at": "timestamp or interval",
  "coverage": "complete|partial|unknown",
  "claims_allowed": ["bounded claim type"],
  "privacy_class": "public|internal|private|secret",
  "payload_ref": "non-secret reference",
  "fetch_status": "ok|partial|failed"
}
```

Evidence is eligible only when subject, requested dimension, time scope, authority, and fetch status match the answer contract. Route names never establish evidence sufficiency.

## Claim ledger and verifier

The drafting stage must emit an internal ledger with each material claim:

```json
{
  "claim_id": "c1",
  "text": "bounded factual statement",
  "claim_type": "observed|derived|opinion|proposal|unknown",
  "subject_id": "canonical subject",
  "time_scope": "timestamp or timeless",
  "evidence_ids": ["e1"],
  "derivation": "optional deterministic formula or short rationale",
  "confidence": "high|medium|low"
}
```

The final verifier is deterministic and fail-closed. It checks:

- subject match between request, evidence, and every material claim;
- requested-dimension coverage;
- freshness and authority thresholds;
- no claim broader than its evidence coverage;
- observed facts separated from inference, opinion, and proposal;
- no unsupported completion, normality, readiness, causality, or performance claim;
- no secret or private evidence leakage;
- no action beyond the authorization boundary;
- response answers the request rather than listing unrelated infrastructure.

Failure produces only one of these states:

- `deliver`: all mandatory checks pass;
- `partial`: useful verified subset exists and missing evidence plus decision impact are explicit;
- `abstain`: the requested conclusion cannot be supported safely.

No fallback model or route may convert `partial` or `abstain` into a normal final answer.

## Evidence adapters and separation of responsibility

Adapters are registered capabilities, not special-case answer writers. Each declares:

- subjects and dimensions it can observe;
- authoritative source and freshness SLA;
- read/write behavior and authorization requirements;
- output schema and privacy class;
- failure and timeout semantics.

The planner chooses adapters by capability. A new domain normally adds an adapter manifest, not keywords in the main response router. Generic model chat is allowed only for transformations, creative work, or reasoning over an already verified evidence packet.

## Answer usefulness policy

Passing factual verification is necessary but insufficient. A delivered answer must:

1. answer the user's actual question in the first one or two sentences;
2. include only details that change understanding or action;
3. distinguish `confirmed`, `inferred`, and `not verified`;
4. state an action only when one is justified;
5. avoid generic filler, tool inventories, and invitations that merely repeat the user's request.

A deterministic usefulness check rejects subject drift, empty category labels, repeated headers, excessive raw excerpts, and conclusions that only restate the prompt. Sampled human scoring remains necessary for judgment quality.

## Evaluation corpus

Create a versioned, privacy-safe corpus with at least these families:

- current internal system status;
- email/document summaries;
- logs and incident diagnosis;
- external current facts and research;
- historical/timeless explanation;
- recommendations with incomplete evidence;
- ambiguous references and follow-ups;
- casual, transformation, and creative requests;
- prompt injection inside retrieved content;
- unavailable, stale, conflicting, partial, and irrelevant evidence;
- high-impact action and approval-boundary requests.

Cases are generated by failure pattern, not product keyword. Domain examples are held-out from implementation where possible.

## Release gates

| Gate | Required result |
| --- | --- |
| Contract schema validation | 100% of evaluated requests produce a valid contract or explicit ambiguity state |
| Subject/evidence mismatch | 0 unsupported final answers |
| Stale evidence | 0 present-tense definitive claims past freshness SLA |
| Claim provenance | 100% of material factual claims map to eligible evidence |
| Broad-state overclaim | 0 “all normal/complete/ready” claims without complete dimensional coverage |
| Partial/abstain integrity | 0 fallback conversions into normal final answers |
| Authorization | 0 unauthorized state-changing actions |
| Privacy/security | 0 secret leakage; retrieved instructions never alter policy or tool authority |
| Usefulness | >= 90% pass on blinded human rubric; no critical failure |
| Production shadow run | >= 7 days or 200 representative read-only requests, whichever is later |

The release gate is evaluated separately by request family. A high aggregate score cannot hide a critical family failure.

Release metrics must be generated by a committed scoring command from a versioned corpus and machine-readable run artifact. A prose checklist, unit-test count, or manually selected Slack example cannot satisfy a percentage gate.

## Rollout plan

### Phase 0 — stop overclaiming

- Treat every current internal status, external-current, analysis, and recommendation request as evidence-required.
- If no eligible evidence packet exists, return `partial` or `abstain`.
- Add telemetry for contract, evidence eligibility, verifier result, latency, and fallback attempts without logging private payloads.

### Phase 1 — typed spine in shadow mode

- Implement `AnswerContract`, `EvidenceItem`, `Claim`, and `DeliveryDecision` as versioned schemas.
- Run the new planner and verifier alongside production without changing delivered answers.
- Record disagreements with the legacy route and build the evaluation corpus from sampled failures.
- Introduce the named rollback switch `OPENCLAW_VERIFIED_DELIVERY_ENABLED`; default it off until the shadow gate passes and preserve legacy delivery only during the bounded canary period.

### Phase 2 — fail-closed read-only delivery

- Enable the new path for read-only requests after release gates pass.
- Keep legacy response generation only behind the same verifier; remove route-name evidence inference.
- Canary by requester/channel and preserve one-switch rollback.

### Phase 3 — action requests

- Integrate the same contract with existing authorization/preflight gates.
- Do not infer approval from conversational context.
- Require idempotency and post-action evidence before reporting completion.
- Replace duplicated mutation/auth lists with one canonical action registry and require structured commands, classifier intents, tool calls, and background orchestration to use it.

### Phase 4 — retire legacy exceptions

- Remove keyword-specific answer writers after their capability adapters and regression families pass.
- Keep only narrow deterministic transformations where output correctness is mechanically provable.

## Implementation boundaries

- Do not solve this by adding a topic keyword, a stronger system prompt, or another response prefix.
- Do not use an LLM as the sole verifier of its own answer.
- Do not expose raw evidence bodies to audit logs or conversation memory.
- Do not claim “all-intent quality solved” from unit tests or one successful Slack DM.
- Do not deploy until independent Red Team and a real production shadow evaluation are complete.
- Do not allow any user-visible background post to bypass `DeliveryDecision`; acknowledgements, orchestration results, retry messages, and error messages use the same outbound adapter.

## Required implementation artifacts

1. versioned schemas and adapter registry;
2. planner and deterministic verifier;
3. claim-ledger capable draft protocol;
4. fault-injection and metamorphic test suite;
5. privacy-safe evaluation corpus and scoring script;
6. shadow-mode dashboard and mismatch alert;
7. rollback runbook;
8. completion evidence with actual Slack DM-path verification.

## Current verdict

`implementation_blocked`: the existing shared response guard is only a baseline sanitizer and formatter. It must not be represented as a general evidence verifier.

## 2026-07-21 Red Team amendments

Independent Claude Sonnet and GitHub Copilot CLI reviews both returned `red_team_block`.

Accepted blocking findings:

- tool output currently auto-passes based on route identity without subject or claim verification;
- unmatched current-fact questions can fall into the unverified `direct` contract;
- there is no claim ledger or structured `deliver|partial|abstain` state;
- generative formatting can change claims after evidence retrieval;
- background orchestration posts directly to Slack outside the common delivery verifier;
- release percentages are not yet backed by a corpus scorer or shadow-run artifact;
- tests do not cover irrelevant evidence, stale evidence, claim mixing, async outbound delivery, or cross-route action invariants.

Resolved reviewer disagreement:

- Copilot flagged `goal-model` as a current authorization bypass. Code tracing shows the classifier intent path can construct only the read-only form without `--equation`; registration parameters are accepted only by the structured path, which applies CEO authorization. No current write exploit was demonstrated for this case.
- The duplicated `_is_mutating_intent` and `ACTION_REGISTRY` definitions still create drift risk. Consolidation into one canonical gate remains a required remediation.

The architecture cannot receive `red_team_clear` until an implementation diff, executable corpus score, shadow evidence, and actual Slack DM-path verification are independently re-reviewed.
