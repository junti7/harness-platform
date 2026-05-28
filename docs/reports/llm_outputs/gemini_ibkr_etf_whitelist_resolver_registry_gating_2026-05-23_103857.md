```json
{
  "strategic_intent": "Summarize the red-team findings, risks, and recommended next actions based on the analysis of the provided code and documentation.",
  "title": "IBKR ETF Whitelist Resolver + Registry Gating Red-Team Report",
  "summary": "I have completed reviewing all provided input artifacts: `scripts/ibkr_cp_client.py`, `scripts/openclaw_codex_bridge.py`, `adapters/content/openclaw_agent.py`, `docs/trading/etf_whitelist_v0.json`, and `docs/reports/instrument_registry.jsonl`. I also noted that `docs/governance/RED_TEAM_REQUEST_IBKR_ETF_2026-05-23.md` was missing. Based on this review, I will now synthesize the information to identify catastrophic failure modes, assess the current hardening steps against the task's checks and notes, and propose further hardening steps for the IBKR ETF whitelist resolver and registry gating process. The following will be presented in a markdown format with sections for Objective, Findings, Risks, and Recommended Next Actions."
}
```
```markdown
# IBKR ETF Whitelist Resolver + Registry Gating Red-Team Report

**Generated At:** 2026-05-23T10:38:57

## Objective
Red-team the IBKR ETF whitelist resolver plan and code changes BEFORE any further execution. Identify catastrophic failure modes (wrong conid, unauthorized mutation, hallucinated tradability), and propose hardening steps.

## Findings

1.  **IBKR Client Portal API (CP API) Client (`scripts/ibkr_cp_client.py`):**
    *   Provides a foundational client for symbol resolution (`secdef_search`) and contract details (`secdef_info`).
    *   Includes `safe_check_connectivity` for pre-flight API reachability and authentication status, crucial for early detection of issues.

2.  **OpenClaw Codex Bridge (`scripts/openclaw_codex_bridge.py`):**
    *   **Whitelist Loading:** Correctly loads ETF whitelist from `docs/trading/etf_whitelist_v0.json`.
    *   **Candidate Normalization:** `_normalize_secdef_candidates` attempts to standardize varied IBKR API responses, which is a necessary step for robust processing.
    *   **Conservative Selection with Confidence:** `_pick_best_candidate` implements a scoring heuristic, prioritizing exact symbol matches and exchange hints, and assigns a `confidence` score. This directly addresses the need for conservative selection and handling ambiguous candidates.
    *   **Read-Only Check:** `command_ibkr_etf_check` provides a safe way to preview resolution results without side effects.
    *   **Gated Approval:** `command_ibkr_etf_approve` is a mutating command that writes to `docs/reports/instrument_registry.jsonl`. It enforces checks for API connectivity and (critically) authenticated status (`authenticated=false` blocks mutation), aligning with the task's note.
    *   **Append-Only Registry:** `_append_instrument_registry` ensures immutable logging of approved mappings.

3.  **OpenClaw Agent (`adapters/content/openclaw_agent.py`):**
    *   **Command Parsing:** Efficiently parses `ibkr` commands, differentiating between `ibkr-etf-check` and `ibkr-etf-approve`.
    *   **High-Risk Action Classification:** `ibkr-etf-approve` is correctly classified as `high` risk, `mutates_state: True`, and `requires_approval: True` in the `ACTION_REGISTRY`.
    *   **CEO Authorization Enforcement:** The `_authorized_for_high_risk` function strictly requires the `requester_user_id` to match `SLACK_CEO_USER_ID` for `ibkr-etf-approve`, fulfilling the "CEO identity + explicit confirm" check.

4.  **ETF Whitelist (`docs/trading/etf_whitelist_v0.json`):**
    *   Clearly defines ETF items with `query`, `exchange_hint`, and `name_hint`, providing essential context for resolution.
    *   Explicitly states "Nothing in this file is a trading instruction," reinforcing that this is for *resolution*, not *execution*.

5.  **Instrument Registry (`docs/reports/instrument_registry.jsonl`):**
    *   Currently empty, designed as an append-only log for approved `conid` mappings.

**Missing Artifact:** `docs/governance/RED_TEAM_REQUEST_IBKR_ETF_2026-05-23.md` was not found.

## Risks

1.  **Wrong `conid` Selection (High Risk):**
    *   **Source:** While `_pick_best_candidate` is conservative, the initial normalization (`_normalize_secdef_candidates`) and subsequent scoring might still be vulnerable to ambiguous IBKR API responses. Specifically, `secdef_search` returns candidates that might not perfectly align with the `etf_whitelist_v0.json` metadata (`type`, `region`, `name_hint`).
    *   **Impact:** Registering an incorrect `conid` could lead to trades of the wrong instrument, incorrect reporting, or other severe financial consequences. The `min_confidence` threshold helps, but a high confidence score does not guarantee correctness, especially if the underlying search results are misleading or incomplete.
    *   **KRX Specific Risk:** The task explicitly mentions `KRX tickers/codes may not uniquely map`. The current system might not be sufficiently robust for these edge cases.

2.  **Hallucinated Tradability (Medium Risk):**
    *   **Source:** The current system resolves `conid` based on contract definition. However, IBKR API responses do not inherently verify "tradability" for a specific account or market conditions. A `conid` can be valid but not tradable due to account restrictions, market hours, or other dynamic factors.
    *   **Impact:** False assumption of tradability could lead to failed trade attempts, wasted operational time, or misrepresentation of asset availability.

3.  **Authentication Bypass (Low Risk, but Critical if Exploited):**
    *   **Source:** The CEO authorization relies on `SLACK_CEO_USER_ID`. If this environment variable is compromised or incorrectly configured, the `ibkr-etf-approve` gate could be bypassed.
    *   **Impact:** Unauthorized individuals could inject arbitrary `conid` mappings into the registry.

4.  **Incomplete Audit Trail for Approvals (Low Risk, High Operational Impact):**
    *   **Source:** While `instrument_registry.jsonl` records approved `conid`s, it currently lacks explicit information about *who* approved the entry (the `requester_user_id`).
    *   **Impact:** Difficulty in auditing, accountability, and debugging specific registry entries.

## Recommended Next Actions

1.  **Enhance `conid` Verification with `secdef_info` Integration:**
    *   **Instruction:** Modify `_pick_best_candidate` or introduce a post-selection verification step in `command_ibkr_etf_check` and `command_ibkr_etf_approve`.
    *   **Details:** For each "best" candidate identified by `secdef_search`, make an additional call to `IbkrCpClient.secdef_info(conid=best_candidate['conid'])`. Compare critical attributes (e.g., `sectype`, `currency`, `exchange`, `tradingClass`, full `description`) from the `secdef_info` response against the original whitelist item's `type`, `region`, `exchange_hint`, and `name_hint`.
    *   **Outcome:** Only allow high `confidence` (and thus auto-approval) if there's a strong match across multiple fields from `secdef_info`, ensuring a higher degree of correctness for the selected `conid`. This would significantly reduce the risk of a "wrong conid".

2.  **Implement Explicit Human Review Workflow for Ambiguous Cases:**
    *   **Instruction:** Develop a Slack-based workflow for `ibkr-etf-check` results with `confidence` scores below the `min_confidence` threshold (e.g., 0.6-0.85).
    *   **Details:** Instead of silently skipping, send a Slack message to a designated channel (e.g., `exec-president-decisions` or a dedicated `ibkr-review` channel) containing the details of the low-confidence whitelist item, the top few candidates, their `confidence` scores, and a clear prompt for manual review. This message should include buttons or a command structure for the CEO to explicitly approve a specific `conid` (potentially with an override of the confidence threshold) or to reject/defer. This makes the implicit human review explicit and auditable.

3.  **Introduce a "Tradability Check" at a Later Stage (Post-Resolution, Pre-Trade):**
    *   **Instruction:** Acknowledge that `conid` resolution does not equate to immediate tradability.
    *   **Details:** Implement a separate pre-trade gate (outside the scope of this `conid` resolver, but crucial for downstream systems) that queries IBKR's trading rules or attempts a dry-run order placement for any `conid` *before* a live trade is initiated. This would address the "hallucinated tradability" risk.

4.  **Enhance Audit Trail for `ibkr-etf-approve`:**
    *   **Instruction:** Modify `_append_instrument_registry` in `scripts/openclaw_codex_bridge.py`.
    *   **Details:** Add the `requester_user_id` (retrieved from the `openclaw_agent` context) to the `instrument_registry.jsonl` entry whenever a new mapping is approved. This provides better accountability and traceability.

5.  **Robust Alerting for IBKR API Failures:**
    *   **Instruction:** Integrate the `send_slack` tool within `command_ibkr_etf_approve` and `command_ibkr_etf_check` for critical failures.
    *   **Details:** If `safe_check_connectivity` returns `ok: false` or `authenticated: false`, or if `client.secdef_search` or `client.secdef_info` throws an exception during an `ibkr-etf-approve` command, send an immediate alert to the `ops-incidents` Slack channel (or a dedicated `ibkr-alerts` channel). This ensures operational awareness of critical API issues.
```
```markdown
# IBKR ETF Whitelist Resolver + Registry Gating Red-Team Report

**Generated At:** 2026-05-23T10:38:57

## Objective
Red-team the IBKR ETF whitelist resolver plan and code changes BEFORE any further execution. Identify catastrophic failure modes (wrong conid, unauthorized mutation, hallucinated tradability), and propose hardening steps.

## Findings

1.  **IBKR Client Portal API (CP API) Client (`scripts/ibkr_cp_client.py`):**
    *   Provides a foundational client for symbol resolution (`secdef_search`) and contract details (`secdef_info`).
    *   Includes `safe_check_connectivity` for pre-flight API reachability and authentication status, crucial for early detection of issues.

2.  **OpenClaw Codex Bridge (`scripts/openclaw_codex_bridge.py`):**
    *   **Whitelist Loading:** Correctly loads ETF whitelist from `docs/trading/etf_whitelist_v0.json`.
    *   **Candidate Normalization:** `_normalize_secdef_candidates` attempts to standardize varied IBKR API responses, which is a necessary step for robust processing.
    *   **Conservative Selection with Confidence:** `_pick_best_candidate` implements a scoring heuristic, prioritizing exact symbol matches and exchange hints, and assigns a `confidence` score. This directly addresses the need for conservative selection and handling ambiguous candidates.
    *   **Read-Only Check:** `command_ibkr_etf_check` provides a safe way to preview resolution results without side effects.
    *   **Gated Approval:** `command_ibkr_etf_approve` is a mutating command that writes to `docs/reports/instrument_registry.jsonl`. It enforces checks for API connectivity and (critically) authenticated status (`authenticated=false` blocks mutation), aligning with the task's note.
    *   **Append-Only Registry:** `_append_instrument_registry` ensures immutable logging of approved mappings.

3.  **OpenClaw Agent (`adapters/content/openclaw_agent.py`):**
    *   **Command Parsing:** Efficiently parses `ibkr` commands, differentiating between `ibkr-etf-check` and `ibkr-etf-approve`.
    *   **High-Risk Action Classification:** `ibkr-etf-approve` is correctly classified as `high` risk, `mutates_state: True`, and `requires_approval: True` in the `ACTION_REGISTRY`.
    *   **CEO Authorization Enforcement:** The `_authorized_for_high_risk` function strictly requires the `requester_user_id` to match `SLACK_CEO_USER_ID` for `ibkr-etf-approve`, fulfilling the "CEO identity + explicit confirm" check.

4.  **ETF Whitelist (`docs/trading/etf_whitelist_v0.json`):**
    *   Clearly defines ETF items with `query`, `exchange_hint`, and `name_hint`, providing essential context for resolution.
    *   Explicitly states "Nothing in this file is a trading instruction," reinforcing that this is for *resolution*, not *execution*.

5.  **Instrument Registry (`docs/reports/instrument_registry.jsonl`):**
    *   Currently empty, designed as an append-only log for approved `conid` mappings.

**Missing Artifact:** `docs/governance/RED_TEAM_REQUEST_IBKR_ETF_2026-05-23.md` was not found.

## Risks

1.  **Wrong `conid` Selection (High Risk):**
    *   **Source:** While `_pick_best_candidate` is conservative, the initial normalization (`_normalize_secdef_candidates`) and subsequent scoring might still be vulnerable to ambiguous IBKR API responses. Specifically, `secdef_search` returns candidates that might not perfectly align with the `etf_whitelist_v0.json` metadata (`type`, `region`, `name_hint`).
    *   **Impact:** Registering an incorrect `conid` could lead to trades of the wrong instrument, incorrect reporting, or other severe financial consequences. The `min_confidence` threshold helps, but a high confidence score does not guarantee correctness, especially if the underlying search results are misleading or incomplete.
    *   **KRX Specific Risk:** The task explicitly mentions `KRX tickers/codes may not uniquely map`. The current system might not be sufficiently robust for these edge cases.

2.  **Hallucinated Tradability (Medium Risk):
    *   **Source:** The current system resolves `conid` based on contract definition. However, IBKR API responses do not inherently verify "tradability" for a specific account or market conditions. A `conid` can be valid but not tradable due to account restrictions, market hours, or other dynamic factors.
    *   **Impact:** False assumption of tradability could lead to failed trade attempts, wasted operational time, or misrepresentation of asset availability.

3.  **Authentication Bypass (Low Risk, but Critical if Exploited):**
    *   **Source:** The CEO authorization relies on `SLACK_CEO_USER_ID`. If this environment variable is compromised or incorrectly configured, the `ibkr-etf-approve` gate could be bypassed.
    *   **Impact:** Unauthorized individuals could inject arbitrary `conid` mappings into the registry.

4.  **Incomplete Audit Trail for Approvals (Low Risk, High Operational Impact):**
    *   **Source:** While `instrument_registry.jsonl` records approved `conid`s, it currently lacks explicit information about *who* approved the entry (the `requester_user_id`).
    *   **Impact:** Difficulty in auditing, accountability, and debugging specific registry entries.

## Recommended Next Actions

1.  **Enhance `conid` Verification with `secdef_info` Integration:**
    *   **Instruction:** Modify `_pick_best_candidate` or introduce a post-selection verification step in `command_ibkr_etf_check` and `command_ibkr_etf_approve`.
    *   **Details:** For each "best" candidate identified by `secdef_search`, make an additional call to `IbkrCpClient.secdef_info(conid=best_candidate['conid'])`. Compare critical attributes (e.g., `sectype`, `currency`, `exchange`, `tradingClass`, full `description`) from the `secdef_info` response against the original whitelist item's `type`, `region`, `exchange_hint`, and `name_hint`.
    *   **Outcome:** Only allow high `confidence` (and thus auto-approval) if there's a strong match across multiple fields from `secdef_info`, ensuring a higher degree of correctness for the selected `conid`. This would significantly reduce the risk of a "wrong conid".

2.  **Implement Explicit Human Review Workflow for Ambiguous Cases:**
    *   **Instruction:** Develop a Slack-based workflow for `ibkr-etf-check` results with `confidence` scores below the `min_confidence` threshold (e.g., 0.6-0.85).
    *   **Details:** Instead of silently skipping, send a Slack message to a designated channel (e.g., `exec-president-decisions` or a dedicated `ibkr-review` channel) containing the details of the low-confidence whitelist item, the top few candidates, their `confidence` scores, and a clear prompt for manual review. This message should include buttons or a command structure for the CEO to explicitly approve a specific `conid` (potentially with an override of the confidence threshold) or to reject/defer. This makes the implicit human review explicit and auditable.

3.  **Introduce a "Tradability Check" at a Later Stage (Post-Resolution, Pre-Trade):**
    *   **Instruction:** Acknowledge that `conid` resolution does not equate to immediate tradability.
    *   **Details:** Implement a separate pre-trade gate (outside the scope of this `conid` resolver, but crucial for downstream systems) that queries IBKR's trading rules or attempts a dry-run order placement for any `conid` *before* a live trade is initiated. This would address the "hallucinated tradability" risk.

4.  **Enhance Audit Trail for `ibkr-etf-approve`:**
    *   **Instruction:** Modify `_append_instrument_registry` in `scripts/openclaw_codex_bridge.py`.
    *   **Details:** Add the `requester_user_id` (retrieved from the `openclaw_agent` context) to the `instrument_registry.jsonl` entry whenever a new mapping is approved. This provides better accountability and traceability.

5.  **Robust Alerting for IBKR API Failures:**
    *   **Instruction:** Integrate the `send_slack` tool within `command_ibkr_etf_approve` and `command_ibkr_etf_check` for critical failures.
    *   **Details:** If `safe_check_connectivity` returns `ok: false` or `authenticated: false`, or if `client.secdef_search` or `client.secdef_info` throws an exception during an `ibkr-etf-approve` command, send an immediate alert to the `ops-incidents` Slack channel (or a dedicated `ibkr-alerts` channel). This ensures operational awareness of critical API issues.
```
```markdown
# IBKR ETF Whitelist Resolver + Registry Gating Red-Team Report

**Generated At:** 2026-05-23T10:38:57

## Objective
Red-team the IBKR ETF whitelist resolver plan and code changes BEFORE any further execution. Identify catastrophic failure modes (wrong conid, unauthorized mutation, hallucinated tradability), and propose hardening steps.

## Findings

1.  **IBKR Client Portal API (CP API) Client (`scripts/ibkr_cp_client.py`):**
    *   Provides a foundational client for symbol resolution (`secdef_search`) and contract details (`secdef_info`).
    *   Includes `safe_check_connectivity` for pre-flight API reachability and authentication status, crucial for early detection of issues.

2.  **OpenClaw Codex Bridge (`scripts/openclaw_codex_bridge.py`):**
    *   **Whitelist Loading:** Correctly loads ETF whitelist from `docs/trading/etf_whitelist_v0.json`.
    *   **Candidate Normalization:** `_normalize_secdef_candidates` attempts to standardize varied IBKR API responses, which is a necessary step for robust processing.
    *   **Conservative Selection with Confidence:** `_pick_best_candidate` implements a scoring heuristic, prioritizing exact symbol matches and exchange hints, and assigns a `confidence` score. This directly addresses the need for conservative selection and handling ambiguous candidates.
    *   **Read-Only Check:** `command_ibkr_etf_check` provides a safe way to preview resolution results without side effects.
    *   **Gated Approval:** `command_ibkr_etf_approve` is a mutating command that writes to `docs/reports/instrument_registry.jsonl`. It enforces checks for API connectivity and (critically) authenticated status (`authenticated=false` blocks mutation), aligning with the task's note.
    *   **Append-Only Registry:** `_append_instrument_registry` ensures immutable logging of approved mappings.

3.  **OpenClaw Agent (`adapters/content/openclaw_agent.py`):**
    *   **Command Parsing:** Efficiently parses `ibkr` commands, differentiating between `ibkr-etf-check` and `ibkr-etf-approve`.
    *   **High-Risk Action Classification:** `ibkr-etf-approve` is correctly classified as `high` risk, `mutates_state: True`, and `requires_approval: True` in the `ACTION_REGISTRY`.
    *   **CEO Authorization Enforcement:** The `_authorized_for_high_risk` function strictly requires the `requester_user_id` to match `SLACK_CEO_USER_ID` for `ibkr-etf-approve`, fulfilling the "CEO identity + explicit confirm" check.

4.  **ETF Whitelist (`docs/trading/etf_whitelist_v0.json`):**
    *   Clearly defines ETF items with `query`, `exchange_hint`, and `name_hint`, providing essential context for resolution.
    *   Explicitly states "Nothing in this file is a trading instruction," reinforcing that this is for *resolution*, not *execution*.

5.  **Instrument Registry (`docs/reports/instrument_registry.jsonl`):**
    *   Currently empty, designed as an append-only log for approved `conid` mappings.

**Missing Artifact:** `docs/governance/RED_TEAM_REQUEST_IBKR_ETF_2026-05-23.md` was not found.

## Risks

1.  **Wrong `conid` Selection (High Risk):**
    *   **Source:** While `_pick_best_candidate` is conservative, the initial normalization (`_normalize_secdef_candidates`) and subsequent scoring might still be vulnerable to ambiguous IBKR API responses. Specifically, `secdef_search` returns candidates that might not perfectly align with the `etf_whitelist_v0.json` metadata (`type`, `region`, `name_hint`).
    *   **Impact:** Registering an incorrect `conid` could lead to trades of the wrong instrument, incorrect reporting, or other severe financial consequences. The `min_confidence` threshold helps, but a high confidence score does not guarantee correctness, especially if the underlying search results are misleading or incomplete.
    *   **KRX Specific Risk:** The task explicitly mentions `KRX tickers/codes may not uniquely map`. The current system might not be sufficiently robust for these edge cases.

2.  **Hallucinated Tradability (Medium Risk):**
    *   **Source:** The current system resolves `conid` based on contract definition. However, IBKR API responses do not inherently verify "tradability" for a specific account or market conditions. A `conid` can be valid but not tradable due to account restrictions, market hours, or other dynamic factors.
    *   **Impact:** False assumption of tradability could lead to failed trade attempts, wasted operational time, or misrepresentation of asset availability.

3.  **Authentication Bypass (Low Risk, but Critical if Exploited):**
    *   **Source:** The CEO authorization relies on `SLACK_CEO_USER_ID`. If this environment variable is compromised or incorrectly configured, the `ibkr-etf-approve` gate could be bypassed.
    *   **Impact:** Unauthorized individuals could inject arbitrary `conid` mappings into the registry.

4.  **Incomplete Audit Trail for Approvals (Low Risk, High Operational Impact):**
    *   **Source:** While `instrument_registry.jsonl` records approved `conid`s, it currently lacks explicit information about *who* approved the entry (the `requester_user_id`).
    *   **Impact:** Difficulty in auditing, accountability, and debugging specific registry entries.

## Recommended Next Actions

1.  **Enhance `conid` Verification with `secdef_info` Integration:**
    *   **Instruction:** Modify `_pick_best_candidate` or introduce a post-selection verification step in `command_ibkr_etf_check` and `command_ibkr_etf_approve`.
    *   **Details:** For each "best" candidate identified by `secdef_search`, make an additional call to `IbkrCpClient.secdef_info(conid=best_candidate['conid'])`. Compare critical attributes (e.g., `sectype`, `currency`, `exchange`, `tradingClass`, full `description`) from the `secdef_info` response against the original whitelist item's `type`, `region`, `exchange_hint`, and `name_hint`.
    *   **Outcome:** Only allow high `confidence` (and thus auto-approval) if there's a strong match across multiple fields from `secdef_info`, ensuring a higher degree of correctness for the selected `conid`. This would significantly reduce the risk of a "wrong conid".

2.  **Implement Explicit Human Review Workflow for Ambiguous Cases:**
    *   **Instruction:** Develop a Slack-based workflow for `ibkr-etf-check` results with `confidence` scores below the `min_confidence` threshold (e.g., 0.6-0.85).
    *   **Details:** Instead of silently skipping, send a Slack message to a designated channel (e.g., `exec-president-decisions` or a dedicated `ibkr-review` channel) containing the details of the low-confidence whitelist item, the top few candidates, their `confidence` scores, and a clear prompt for manual review. This message should include buttons or a command structure for the CEO to explicitly approve a specific `conid` (potentially with an override of the confidence threshold) or to reject/defer. This makes the implicit human review explicit and auditable.

3.  **Introduce a "Tradability Check" at a Later Stage (Post-Resolution, Pre-Trade):**
    *   **Instruction:** Acknowledge that `conid` resolution does not equate to immediate tradability.
    *   **Details:** Implement a separate pre-trade gate (outside the scope of this `conid` resolver, but crucial for downstream systems) that queries IBKR's trading rules or attempts a dry-run order placement for any `conid` *before* a live trade is initiated. This would address the "hallucinated tradability" risk.

4.  **Enhance Audit Trail for `ibkr-etf-approve`:**
    *   **Instruction:** Modify `_append_instrument_registry` in `scripts/openclaw_codex_bridge.py`.
    *   **Details:** Add the `requester_user_id` (retrieved from the `openclaw_agent` context) to the `instrument_registry.jsonl` entry whenever a new mapping is approved. This provides better accountability and traceability.

5.  **Robust Alerting for IBKR API Failures:**
    *   **Instruction:** Integrate the `send_slack` tool within `command_ibkr_etf_approve` and `command_ibkr_etf_check` for critical failures.
    *   **Details:** If `safe_check_connectivity` returns `ok: false` or `authenticated: false`, or if `client.secdef_search` or `client.secdef_info` throws an exception during an `ibkr-etf-approve` command, send an immediate alert to the `ops-incidents` Slack channel (or a dedicated `ibkr-alerts` channel). This ensures operational awareness of critical API issues.
```