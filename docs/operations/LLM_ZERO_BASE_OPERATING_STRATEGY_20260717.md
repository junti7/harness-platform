# Harness LLM Zero-Base Operating Strategy

Date: 2026-07-17
Status: proposed operating baseline
Owner: CEO Chief of Staff / Codex

## Executive Decision

Harness must operate as if premium API credit is zero unless a task has an explicit, measured budget. A subscription, installed CLI, or configured API key is **not** evidence of remaining tokens or free API quota.

Default order:

1. deterministic code, SQL, parsers, templates, and cached results
2. local Ollama models on the available machine
3. included-subscription CLI capacity when authenticated and the task is inside that subscription's allowance
4. paid API only after a per-task budget check and human approval

No workflow may call a premium model merely because it is available.

## Verified Inventory (2026-07-17)

This is an operational snapshot, not a billing statement.

| Resource | Local evidence | Remaining quota evidence | Default treatment |
|---|---|---|---|
| Codex / ChatGPT Pro | `codex-cli 0.144.5` installed | Exact remaining Codex tokens are not exposed by the local CLI | Primary for code, repo analysis, and bounded docs work; do not assume unlimited capacity |
| Claude | CLI installed; `claude auth status` returned `loggedIn=false` | None | Disabled until authenticated; never use Claude API as silent fallback |
| Gemini | CLI installed; API key variable exists | No current quota/credit proof; prior Gemini credit was exhausted in project policy | Disabled by default; enable only with current quota evidence |
| GitHub Copilot | CLI installed | CLI reported no authentication in this environment | Developer helper only after login; never a required runtime dependency |
| Ollama | Binary installed; local host probe was blocked in this shell and model inventory was unavailable | Local capacity must be probed before a run | First choice for free batch work; fail closed to queue if unavailable |
| Embeddings | `nomic-embed-text` configured; historical Ollama usage exists | Current Ollama server not proven live in this shell | Local embedding first; no automatic paid embedding fallback |

ChatGPT Pro subscription and OpenAI API billing are separate. The former must not be counted as API credit. The same separation applies to Claude/Gemini/Copilot subscriptions versus API keys or quotas.

## Work Classes and Routing

| Work class | First executor | Escalation | Premium default |
|---|---|---|---|
| file parsing, JSON/CSV normalization, link checks, schema checks | Python/SQL/rules | none | forbidden |
| dedup, language/topic classification, short extraction, source tagging | Ollama local | Codex only for sampled audit | forbidden |
| embeddings and retrieval candidate generation | Ollama `nomic-embed-text` | stop and queue if unavailable | forbidden |
| 500-token source triage and rough summary | Ollama local | Codex sample review | forbidden |
| code implementation and tests | Codex subscription capacity | human review; Copilot optional | API calls forbidden unless explicitly approved |
| repo-wide architecture or difficult debugging | Codex first | authenticated Claude/Copilot second opinion when requested | paid API off by default |
| executive synthesis / strategy memo | Codex bounded draft | Claude only if authenticated and task is high-value | one premium call maximum |
| long PDF/multimodal review | local extraction/OCR first | Gemini only with verified credit | no automatic fallback |
| legal, paid offer, investment, capital action | deterministic checklist + Codex draft | human + explicitly ordered cross-LLM review | must not auto-spend |
| customer-facing publish | template + local QA + Codex fact pass | VP, Legal, QA, CEO gates | premium only with approval |

## Call Gates

Every model call must carry:

- `task_id`, `artifact_path`, `purpose`, `provider`, `model`
- estimated input/output tokens
- `estimated_cost_usd` and `approval_id` when cost is non-zero
- fallback reason when the primary route was unavailable
- output path and retention class

Hard gates:

- local route first for all batch work
- premium API route is disabled when quota is unknown
- no same-model fallback masquerading as cross-LLM verification
- no automatic Gemini/Claude/OpenAI retry loop
- max one premium call per artifact by default
- daily paid API budget default: `$0`; changing it requires CEO approval
- per-task paid API budget default: `$0`; exception must record rationale and expected value
- stop the batch when budget telemetry is unavailable; queue for review instead

The current `$1` `DAILY_COST_LIMIT_USD` is not a zero-cost policy by itself. It is only a ceiling and must not silently authorize spending. Set it to `0` for the zero-base profile.

## Pipeline Shape

```text
raw evidence
  -> deterministic normalize/hash/filter
  -> Ollama classify/dedup/short extract
  -> local retrieval + evidence packet
  -> Codex bounded synthesis (only selected packets)
  -> human/VP/Legal/QA gates
  -> publish or queue
```

Premium models never receive the raw source firehose. They receive a small evidence packet containing source IDs, excerpts, and explicit questions.

## Local Model Policy

Recommended local profiles:

- `gemma2:27b` or the strongest available local instruct model: classification, extraction, Korean short summaries
- `qwen2.5:1.5b`: timeout fallback only, never final factual judgment
- `nomic-embed-text`: embeddings

If Ollama is unavailable, do not route batch work to a paid API automatically. Persist a queue item with `local_model_unavailable` and continue deterministic work only.

## Measurement

Track weekly:

- local vs premium call count
- tokens by provider/model
- paid API dollars and subscription dollars separately
- cost per useful signal
- local acceptance rate after Codex audit
- queue age caused by local capacity failure
- premium calls prevented by the gate

Success target for the first 30 days:

- at least 90% of filtering/classification/short-summary calls local or deterministic
- zero unapproved paid API calls
- premium calls limited to selected synthesis/review artifacts
- every unavailable provider recorded, never silently substituted

## Immediate Actions

1. Keep Claude/Gemini/Copilot out of automatic runtime until each is authenticated and quota status is recorded.
2. Make Ollama health a preflight requirement for batch jobs; queue instead of paid fallback.
3. Change the zero-base profile to `DAILY_COST_LIMIT_USD=0` and require an explicit task budget for exceptions.
4. Separate `subscription_status`, `api_key_configured`, `cli_authenticated`, `quota_verified`, and `last_probe_at` in the inventory record.
5. Remove model-name copy/paste errors from the cost dashboard; subscription labels must match actual provider/model.
6. Reconcile `CLAUDE.md`, `AGENTS.md`, and this document before enabling any premium automation.

## Residual Limits

The exact remaining token balance for ChatGPT Pro/Codex, Claude, Gemini, and Copilot cannot be inferred from this repository or local CLI version output. A user-account billing page or authenticated provider quota endpoint is required. Until that evidence exists, the safe state is `quota_unknown`, not `available`.
