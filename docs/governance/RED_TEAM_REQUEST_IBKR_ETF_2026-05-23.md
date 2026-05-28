# RED TEAM REQUEST — IBKR ETF Whitelist Resolver (Phase 1)

- Date: 2026-05-23
- Owner: Codex (engineering)
- Scope: `IBKR CP API` 기반 ETF 후보 → conid 후보화 → CEO confirm 시 append-only registry 반영
- Goal: “틀린 종목 매핑/권한 오판/자동 실행” 같은 catastrophic 실패를 사전에 차단

## What Changed (Artifacts)

- New: `scripts/ibkr_cp_client.py`
- New: `docs/trading/etf_whitelist_v0.json`
- New: `docs/reports/instrument_registry.jsonl` (append-only)
- Update: `scripts/openclaw_codex_bridge.py`
  - Add `ibkr-etf-check` (read-only)
  - Add `ibkr-etf-approve` (mutating internal registry; high-confidence only)
- Update: `adapters/content/openclaw_agent.py`
  - Add structured routing for “IBKR/ETF/whitelist” → bridge commands
  - Mark `ibkr-etf-approve` as mutating intent (CEO confirm required)

## Intended Behavior (Ground Truth)

1. Default query from Slack:
   - “IBKR ETF 화이트리스트 점검” → `ibkr-etf-check` (read-only)
2. Output is *candidates* + conservative “best” pick with confidence.
3. No trading, no order placement, no external mutation.
4. Only when CEO says confirm + approve intent:
   - `ibkr-etf-approve` appends **only high-confidence (>=0.85)** mappings to `instrument_registry.jsonl`.
5. If IBKR CP API is down or not authenticated, return “blocked + instructions”, never hallucinate results.

## Red-Team Questions (Must Answer)

1. Wrong-instrument risk:
   - How could `secdef/search` return ambiguous candidates (same symbol multiple exchanges/currencies)?
   - Does the current heuristic allow a wrong conid to be auto-recorded?
2. Authentication/session risk:
   - CP API can be reachable but `authenticated=false`.
   - Does the code correctly block mutation in that state?
3. Authorization boundary:
   - Can a non-CEO user trigger `ibkr-etf-approve` through phrasing tricks?
4. Auditability:
   - Are we recording enough metadata to debug why a conid was selected?
   - Is append-only registry sufficient or do we need an explicit “superseded” mechanism?
5. Data leakage:
   - Any possibility that tokens/credentials are logged or returned to Slack?
6. Rule-based trap:
   - Does intent routing rely too much on regex/keywords?
   - Is there a safer fallback (“needs_confirm / needs_disambiguation”)?

## Non-Negotiable Safety Requirements

- Never claim “tradable / permission ok” unless explicitly verified by IBKR API response.
- Any mutation (`ibkr-etf-approve`) must require:
  - CEO identity (Slack user id)
  - explicit “confirm”
  - conservative confidence threshold (default 0.85)
- Candidate ambiguity must degrade to “human confirm required”, not “auto-best”.

## Expected Outputs

Each reviewer returns markdown with sections only:
1. Objective
2. Findings
3. Risks
4. Recommended Next Actions

Required verdict per reviewer:
- `red_team_clear` or `red_team_block` (with rationale)

