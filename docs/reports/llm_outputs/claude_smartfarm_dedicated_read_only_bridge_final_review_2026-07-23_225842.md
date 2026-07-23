All artifacts present and verified. Writing the review.

## 1. Objective

Final red-team review of the dedicated `smartfarm-market-research` OpenClaw skill and `scripts/openclaw_smartfarm_research_bridge.py`. Confirm the bridge parser exposes **only** `plan/search/open/extract/validate` (no form-fill/cart/order/payment/GPIO/actuator), and that the underlying validator still enforces six categories, direct/fresh evidence, resolved recommended/alternate checks, and the ESP32 Arduino-framework ADC1 architecture. Return APPROVE or BLOCK.

## 2. Findings

All five input artifacts present and read. Tests pass (`7 passed in 0.01s`).

- **Read-only command surface — confirmed.** `build_parser()` (`openclaw_smartfarm_research_bridge.py:60-97`) registers exactly `plan`, `validate`, `search`, `open`, `extract`. No fill/cart/order/pay/gpio/pump subparser exists. The three browsing commands delegate to `browser_search` / `browser_open(extract_text=True)` / `browser_extract` — all read-only. The write-capable `browser_fill` (found at `browser_control.py:205`, does `page.fill/click`) is **not imported and not exposed** by this bridge. `test_dedicated_openclaw_parser_exposes_only_read_only_commands` asserts the exact set and the absence of `{fill,cart,order,pay,gpio,pump}`.
- **Six categories — enforced.** Catalog has 6 items; `build_research_plan` emits all six; `validate_report` iterates every expected item requiring `MIN_CANDIDATES=3` and exactly one `recommended` (`smartfarm_market_research.py:218-227`). Test asserts `len(plan["items"]) == 6`.
- **Direct / fresh evidence — enforced.** `_is_direct_http_url` rejects search-result hosts (google/naver/bing/duckduckgo, lines 18-26, 111-120); `observed_at` must be tz-aware ISO8601 within the last 14 days (lines 170-178); recommended candidates require ≥2 distinct evidence URLs (163-168).
- **Resolved recommended/alternate checks — fail-closed.** For both `recommended` and `alternate`, any required check whose status ∉ `{True,"verified","pass","yes"}` is flagged unresolved, and each check must carry a direct `evidence_url` (lines 191-214). Covered by `test_recommended_...` and `test_alternate_with_unknown_check_fails_closed`.
- **ESP32 Arduino-framework ADC1 — present.** `controller_architecture` names "ESP32 programmed with the Arduino framework", Raspberry Pi gateway, and the ADC1/Wi-Fi soil-sensing rule (`smartfarm_market_research.py:63-70`); catalog item `soil_sensor_and_watering_pump` carries `esp32_adc1_compatibility`, `adc_calibration_method`, `normally_off_fail_safe`, `food_safe_tubing`; SKILL.md §"Required research behavior" restates it. Test asserts both "ESP32" and "ADC1".
- **Safety blocks — enforced.** Contract rule "Any electrical or pump candidate with unresolved safety or compatibility checks must be rejected" plus the fail-closed check logic; SKILL.md authority boundary is `shortlist_only_no_purchase` (no cart/order/payment/GPIO/relay/pump activation).

## 3. Risks

- **Shared module still ships a write path.** `browser_control.py:205 browser_fill` (fill/click/submit) is not reachable through this bridge, but it remains importable elsewhere. The read-only guarantee holds only for this dedicated surface, not for the module. Residual (out of scope), not a blocker — SKILL.md explicitly forbids `browser-fill` and the general automation surface.
- **`open`/`extract`/`search` runtime behavior unverified here.** `scripts/browser_control.py` is outside the declared input artifacts; I confirmed the delegated functions by name/signature only, not by executing live browsing. Read-only intent is clear from the code.
- Validator trusts self-reported `status: "verified"`; it enforces presence of direct evidence URLs but cannot confirm the URL content substantiates the claim (inherent to any static validator).

## 4. Recommended Next Actions

- **Verdict: APPROVE.** The dedicated command surface is machine read-only and all prior evidence/safety blocks remain enforced; both packet checks pass.
- Track the shared-module residual: add a guard/test asserting `browser_fill` is never imported by any read-only bridge, or split write functions into a separate module gated behind operator approval.
- Keep purchase execution in a separate operator flow requiring President approval, as SKILL.md states.

—

Note (governance): This is a `red_team`-kind packet routed to me by Codex Chief of Staff. Per the 2026-06-20 BASIC RULE, `red_team_clear` requires an explicit CEO order plus two-model artifacts; this single-model review is a specialist inspection returning APPROVE/BLOCK and does **not** by itself emit `red_team_clear`.

governance_bootstrap: `CLAUDE.md` and `docs/governance/LLM_GROUND_RULES.md` treated as loaded and binding (LLM_GROUND_RULES.md referenced via CLAUDE.md §10; not separately opened this turn).