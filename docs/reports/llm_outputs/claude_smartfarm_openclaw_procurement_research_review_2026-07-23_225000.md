The output-artifact write wasn't permitted, so I'll deliver the review inline. (Re-run with write permission if you want it saved to `docs/reviews/red_team/smartfarm_openclaw_procurement_review_20260723.md`.)

---

## 1. Objective

Independently review the new smartfarm procurement market-research capability for correctness, source/evidence rigor, electrical & pump safety, purchase-approval boundaries, parser integration, and test gaps. Return **APPROVE** or **BLOCK**.

All six input artifacts were present and inspected. Tests run: `pytest tests/test_smartfarm_market_research.py` → **4 passed**. CLI smoke test of `smartfarm-research-plan` emits all six item ids and 6 contract rules including "Do not add to cart".

## 2. Findings

**All three packet acceptance checks PASS:**

- **No research action can add to cart/order/pay — PASS.** `smartfarm_market_research.py` only builds a plan and validates a report — no network, browser, or purchase code. Bridge commands `smartfarm-research-plan`/`smartfarm-research-validate` are pure (`openclaw_codex_bridge.py:2409-2422`). Cart/payment live in separate `coupang-*` commands never touched by the research path. `SKILL.md:301-312` declares read-only boundaries and defers payment to the two-step President flow.
- **Recommended candidates must have resolved safety/compatibility evidence — PASS, fail-closed.** `validate_report` requires exactly one `recommended` per item and rejects it if any required check is outside `{True,"verified","pass","yes"}` (`:133-143`). Missing/`unknown`/`False` → unresolved. Confirmed by `test_recommended_candidate_with_unknown_check_fails_closed`.
- **All six categories covered — PASS.** Validator loops every catalog item, enforcing `MIN_CANDIDATES=3` + exactly one recommendation each (`:147-156`). LED, timer/plug, and pump carry the electrical/pump checks (`kc_or_equivalent_safety_mark`, `rated_current_a`, `separate_power_supply`, `normally_off_fail_safe`, `relay_or_mosfet_requirement`).

**Gaps:**
1. **(Medium) Contract rule not machine-enforced for `alternate`.** The plan rule and `SKILL.md:311-312` say a mains/pump item with unresolved safety "must be rejected, not ranked as an alternate." The validator enforces resolved checks **only for `recommended`** (`:133`) — an unsafe electrical/pump *alternate* passes silently. Bounded (purchase target stays gated; research is read-only) but rule and gate diverge.
2. **(Low)** "≥2 evidence URLs for recommended" is unenforced (validator requires ≥1 for all, `:119-121`); rule is "when possible".
3. **(Low)** `product_url` only checked for http(s) prefix (`:116-118`); "never a search-result URL" not detected.
4. **(Low)** No `observed_at` freshness check despite the "current price" objective.
5. **(Low)** `latest.md` Korean mobile summary is unvalidated — only the JSON is gated (conflicts with mobile-first emphasis).
6. **(Low)** `phase: later` pump is forced to 3 candidates + 1 recommendation identically to now-phase items.
7. **(Cosmetic)** `SKILL.md` has duplicate section numbers (two "22", two "23").

## 3. Risks

- **Safety (bounded):** unsafe electrical/pump *alternate* can survive validation (Finding 1); blast radius is the shortlist, not a purchase.
- **Command-surface proximity:** research shares the bridge with `coupang-cart`/`coupang-pay-approve`; mitigated by explicit SKILL boundaries + two-step payment, but manual chaining is possible.
- **Evidence rigor:** search-result URLs, stale prices, single-source recommendations rely on operator discipline, not the machine gate.

## 4. Recommended Next Actions

1. **(Should)** Enforce Finding 1: for items with safety/electrical/pump markers, fail any `alternate` with unresolved checks (force `reject`); add a mirror test for the `alternate` case.
2. **(Nice)** Enforce ≥2 evidence URLs for the recommended candidate.
3. **(Nice)** Add an `observed_at` recency check to back the "current price" objective.
4. **(Nice)** Fix duplicate `SKILL.md` section numbering.

---

**Verdict: APPROVE** for read-only research/shortlist use. All three packet checks pass and the recommended-candidate safety gate is fail-closed. Apply Finding 1 before treating the validator as the sole safety gate for electrical/pump *alternates*. This is a single-model independent review, not a CEO-ordered cross-LLM `red_team_clear`.