## Code Review: OpenClaw harness_saju_query Follow-up Fix

**APPROVE** — with one minor observation worth tracking.

---

### Findings by Change

#### `saju_calendar.py` — Stale explicit date override

**✅ Correct.** The multi-match logic (`_DATE_RE.finditer`, pick `max` by numeric tuple) correctly replaces the *latest* explicit date when a relative keyword (`오늘` etc.) is also present. The replacement is done *before* the `pattern.sub` call, so the relative keyword still gets normalized via `해당일(Asia/Seoul 기준 {marker})`. Order of operations is safe.

**Observation:** `max` by `(year, month, day)` tuple is correct for Korean date ordering, but it implicitly assumes no two explicit dates are identical. If a pathological question repeats the same date string twice, `max` still produces a deterministic (though arbitrary-choice) result — acceptable.

#### `saju_calendar.py` — 오전/오후 birth time

**✅ Correct.** The refactored flow is clean:
- `밤 N시생/출생` → raise (ambiguous, no AM/PM equivalent)
- `오전|오후|a.m.|p.m. N시생/출생` → convert to 24h via standard rules (12 AM → 0, 12 PM → 12, others ±12)
- 24h numeric fallback path unchanged

The guard `if hour is not None: raise ValueError("...중복...")` correctly blocks a question that contains *both* a 지지 branch name and an 오전/오후 numeric time — good fail-closed behavior.

**⚠️ Minor:** The regex `(?:생|출생)` is *required* for `twelve_hour` match, but the preceding `any_numeric_birth_hour` pattern also requires `(?:생|출생)`. This is consistent. However, note that `오전 10시` alone (without `생`/`출생`) would not be caught by `twelve_hour` and would fall through to `any_numeric_birth_hour` without matching `explicit_hour`, triggering the 24h-format error. This is arguably the correct strict behavior for malformed input, but worth documenting if user-facing error messages need to guide correction.

#### `notebook_query_planning.py` — Section aliases (builder + assessor)

**✅ Correct.** The `section_requirements` filter cleanly identifies the canonical label set `{"전체운","재물운","건강운","대인운","주의사항"}` within requirements and appends the label-preservation instruction to the expert contract.

The assessor `elif` chain adds alias-aware markers for each section before falling through to the generic `elif requirement not in text` — the ordering is correct (specific cases before generic).

**Observation:** `"재물"` alone in the marker list for `재물운` is a very short token and could theoretically appear in unrelated text (e.g., "재물 욕심"). Acceptable risk given domain context, but a slightly tighter match like `"재물운"` as primary and `"금전운"` as alias would be more precise if false-positive rate becomes an issue.

#### Tests

**✅ Adequate coverage.** The four new tests cover:
- Section alias acceptance in assessor (`test_delivery_contract_accepts_saju_domain_section_aliases`)
- Section label preservation in grounded question (`test_saju_expert_prompt_preserves_requested_section_labels`)
- Stale date override (`test_relative_saju_date_overrides_stale_explicit_target`)
- 12-hour acceptance (parametrized: 오전/오후/PM/p.m.) and `밤` rejection

One gap: no test exercises the `branch + 오전/오후 numeric` conflict guard (the "중복" raise path). Not a blocker — rare edge, fail-closed.

---

### Summary

| Area | Status | Note |
|---|---|---|
| Stale date override | ✅ | Correct; identical-date edge benign |
| 오전/오후 12h parsing | ✅ | Correct AM/PM math; `밤` correctly kept as error |
| Section alias contract | ✅ | Builder + assessor consistent |
| `"재물"` marker breadth | ⚠️ | Low false-positive risk in domain; monitor |
| Missing `생` suffix edge | ⚠️ | Correct strict behavior; document if UX needed |
| Test coverage | ✅ | Core paths covered; branch+12h conflict path minor gap |

**APPROVE.** No blocking defects. The two minor observations are acceptable for production and can be addressed in a follow-up if telemetry surfaces false positives.
