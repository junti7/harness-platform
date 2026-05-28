The `RED_TEAM_REQUEST_IBKR_ETF_2026-05-23.md` input artifact does **not exist** at `docs/governance/` — only the request packet itself plus the four code/data artifacts were available. Red-teaming below is based on the packet's stated objective/checks and the source I could read.

---

## 1. Objective

Cross-LLM red-team of the IBKR ETF whitelist resolver (`ibkr-etf-check` / `ibkr-etf-approve`) and `instrument_registry.jsonl` gating, *before* CEO `ibkr-etf-approve` is run for the first time. Surface catastrophic failure modes — wrong `conid`, unauthorized state mutation, hallucinated tradability — and propose hardening before any auto-write.

## 2. Findings

**A. Wrong-conid failure modes (high severity)**

- `_pick_best_candidate` (`scripts/openclaw_codex_bridge.py:569-612`) treats `sectype in {"ETF","STK"}` as equally valid. A plain stock that happens to share a numeric/short ticker (e.g. JP `"2638"`, EU `"2B76"`, KRX 6-digit codes that collide globally) can earn the full `1.0 (exact symbol) + 0.5 (exch hint) + 0.2 (sectype STK) = 1.7/1.7 → confidence 1.0` and be auto-written as an "ETF" mapping. Whitelist `type:"etf"` is never enforced against candidate `sectype`.
- `name_hint` (e.g. "KODEX 200", "TIGER Fn반도체TOP10") is present in `etf_whitelist_v0.json` but **never consulted** in the scorer. The single strongest disambiguation signal is unused.
- `exchange_hint` is compared raw-uppercase: whitelist uses `"KRX"`, but IBKR responses for Korean listings commonly return `"KSE"`/`"SEHK"`/region codes — exch hint will silently fail to add weight, and there's no penalty for an exchange mismatch.
- For KRX entries the `query` is the 6-digit local code (`"069500"`). IBKR `secdef/search` typically returns localSymbol or the issuer ticker — exact symbol-string match on a 6-digit code is fragile and asymmetric across regions.

**B. Authorization / mutation gate gaps (high severity)**

- `command_ibkr_etf_approve` checks `auth.get("authenticated") is False` (`bridge.py:735`). If the gateway response is `{}`/missing the `authenticated` key, `auth.get(...)` returns `None`, `None is False` → **False**, and the guard is bypassed. Packet check #1 ("CP API reachable but authenticated=false; block mutation") is **violated for the missing-key case**.
- `--min-confidence` has **no floor**. A CEO-authorized call with `--min-confidence 0.0` auto-writes every best pick regardless of ambiguity. Packet check #3 ("ambiguous → human confirm, not auto-best") is structurally violable.
- Slack intent detection (`adapters/content/openclaw_agent.py:964-983`) fires `ibkr-etf-approve` on `(approve|확정|등록|반영|기록) AND (confirm|진행|실행|확인완료)`. The word "진행" or "실행" alone in a casual sentence will pass the confirm half, and a Korean "ibkr etf 등록 진행" yields an approve intent. Identity gate is `SLACK_CEO_USER_ID` equality (`openclaw_agent.py:1197-1208`) — that's a single factor; there is no per-request nonce / decision-card echo / second tap.
- The bridge writes to `instrument_registry.jsonl` without a `correlation_id`, decision-card reference, or AR ticket. No audit linkage from registry row → CEO approval event.

**C. Hallucinated tradability**

- `secdef_info` exists in the client but is **never called**. Approve records `conid/symbol/exchange/currency/sectype/confidence` from `secdef_search` alone. IBKR account permissioning (Korean market subscription, UCITS distribution restrictions, fractional/PEA flags) is not checked. Downstream consumers will reasonably read an `instrument_registry.jsonl` row as "tradable for our account" — packet check #1 ("never assert tradable/permission unless verified") is broken by silent omission.
- `command_ibkr_etf_check` does **not** block on `authenticated=false` (it only blocks on `preflight.ok=false`). It proceeds to call `secdef_search`, which often returns empty/garbage when unauthenticated, producing a misleading "candidates=0" report that looks like a clean negative result.

**D. Registry integrity**

- `_append_instrument_registry` is pure append, no dedupe key, no `supersedes`/`version`, no `correlation_id`. Re-running approve duplicates rows; first-vs-last semantics are undefined for consumers.
- File-level `flock` is used (`bridge.py:669`) but the registry has **no schema validator** on read (`docs/reports/instrument_registry.jsonl` is currently empty — 1 line/0 bytes per `wc`). First write defines de-facto schema with no test.

**E. Network posture**

- `IBKR_CP_TLS_VERIFY` defaults to **False** (`scripts/ibkr_cp_client.py:41`). Acceptable for `https://localhost:5000` with the standard CP self-signed cert, but `IBKR_CP_API_BASE_URL` is env-overridable with no hostname guard — a misconfigured remote URL would silently MITM-allow.

**F. Error handling**

- Inside `command_ibkr_etf_approve` the per-item `secdef_search` loop is **not** wrapped: a single IBKR 500/timeout mid-loop raises out, dropping all rows accumulated so far and producing a stack trace to the CEO surface, with no partial audit.

## 3. Risks

| Risk | Likelihood | Impact | Notes |
|------|-----------|--------|-------|
| Wrong-conid persisted (STK masquerading as ETF; ticker collision on JP/EU/short codes) | Medium-High | **Catastrophic** if a downstream trader treats registry as ground truth | sectype gate + name_hint match missing |
| Auto-approve fires from loose Korean NLU on a CEO message | Medium | High (writes registry without intent) | Add explicit `confirm <nonce>` flow |
| `authenticated` key absent → mutation guard bypass | Low-Medium | High (writes without auth) | One-line fix |
| `--min-confidence` set below 0.85 | Low (op error / fat-finger) | High | Enforce server-side floor |
| Tradability inferred from registry presence | High (consumer assumption) | High | Add explicit `permission_verified:false` flag |
| Duplicate / un-versioned registry rows | High over time | Medium | Add `supersedes`/dedupe |
| Remote `IBKR_CP_API_BASE_URL` with `tls_verify=False` | Low | High | Hostname allowlist (`localhost`/`127.0.0.1`) |

## 4. Recommended Next Actions

Block `ibkr-etf-approve` until at least items 1–5 land.

1. **Sectype hard-gate**: in `_pick_best_candidate`, drop any candidate whose `sectype` is not in the whitelist item's declared type set (whitelist `type:"etf"` → require `sectype` to match `ETF` *or* `STK` *only if* description/name match passes name_hint). Refuse to auto-pick when the only match is `STK`.
2. **Use `name_hint`**: add a normalized fuzzy match (drop spaces/case/parens) of candidate `description`/`name` vs `name_hint`. Make it a *required* contributor — `confidence ≥ 0.85` requires either exact symbol+sectype+exchange OR symbol+name_hint match.
3. **Fix auth guard**: `if auth.get("authenticated") is not True: block` (treat missing key as not-authenticated). Apply the same check inside `command_ibkr_etf_check` and surface "unauthenticated — results unreliable" rather than running `secdef_search`.
4. **Cap `--min-confidence` server-side**: clamp to `max(0.85, arg)`, log if user passed lower. Optionally remove the CLI flag for the CEO surface entirely.
5. **Ambiguity → human confirm**: when top-2 candidates are within 0.15 score of each other, or when no candidate clears 0.85, write a *pending* record (separate file, e.g. `instrument_registry_pending.jsonl`) listing all candidates, and require a per-item `ibkr-etf-approve --item-id krx-069500 --conid <X> --correlation-id <Y>` to commit. No batch auto-write across ambiguous items.
6. **Verify permission**: call `secdef_info` on the selected conid and record both `permission_verified:false` and any `tradingPermissions`/`isUS`/restriction flags returned. Until IBKR returns explicit tradability evidence, persist `tradable:"unverified"` — never absent, never true-by-default.
7. **Correlation + audit**: require `--correlation-id` (decision-card ID or AR ticket) on `ibkr-etf-approve`; embed it in every appended row and in an `ar_tracker.jsonl` AR-completion entry.
8. **Slack confirm hardening**: change intent rule to require an *explicit* token, e.g. `ibkr etf approve confirm <correlation-id>`. Reject bare "진행"/"실행" and require the correlation-id echoed from the decision card; reject if the surface is not the CEO DM.
9. **Per-item exception handling**: wrap the per-symbol `secdef_search` in the approve loop with try/except, mark failures explicitly in the output, and still write a `failed_resolution` audit row.
10. **Network guard**: refuse to start the client if `IBKR_CP_API_BASE_URL` host is not in `{localhost, 127.0.0.1, ::1}` and `IBKR_CP_TLS_VERIFY=false`.
11. **Registry schema**: add a one-shot validator on append (required keys, conid is digits, confidence in `[0,1]`, `permission_verified` present) and a `supersedes` field; write a test that loads `instrument_registry.jsonl` and rejects duplicates by `(item_id, conid)`.
12. **Cross-LLM re-review** (per `RED_TEAM_PROTOCOL.md`): once items 1–7 are coded, request Gemini and Codex second opinions on the patched scorer + auth guard before any CEO `confirm`. Record `red_team_clear` only on 2-of-3 approve, with the sectype/STK and `authenticated`-key bugs treated as non-negotiable findings (must be fixed, not voted past).

**Missing artifact note:** `docs/governance/RED_TEAM_REQUEST_IBKR_ETF_2026-05-23.md` was listed as input but is not present in the repo (`docs/governance/` directory listed; file absent). If the request memo contains acceptance criteria beyond the three `checks` in the packet, this review may be incomplete on that axis — please surface the memo or confirm the packet's checks are the full spec.