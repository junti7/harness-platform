# OpenClaw Verification Evidence Contract

Date: 2026-07-31
Owner: CEO
Status: implemented, pending production replay

## Incident

For the request `쿠팡 띄워서 푸른친구들 효소력 가격 알아봐`, OpenClaw opened only the
Coupang home page, skipped `harness_screen_inspect`, called `web_search`, and then stated
52,200원, 52,780원, and 59,850원 as current visible prices. The web-search trajectory did not
contain those product/price records. A later screen-inspection attempt returned
`screen_inspect_not_bound_to_routed_owner_request`.

This was not merely imprecise wording. It was an unsupported claim presented as observed fact.

## Root causes

1. The Coupang intent matcher required explicit search wording and missed
   `쿠팡 띄워서 <product> 가격 알아봐`.
2. Browser opening was treated as evidence of screen observation.
3. `web_search` remained callable after GUI evidence routing failed.
4. Final model prose had no server-side evidence validator.
5. Screenshots were not attached through the structured reply payload.
6. Generated Peekaboo captures had no delivery-settled Trash lifecycle.

## Enforced contract

### GUI and Coupang

- Coupang price/search requests open the exact search URL and must call
  `harness_screen_inspect`.
- `web_search`, `web_fetch`, shell, Browser MCP, and direct Peekaboo calls are blocked during the
  routed turn.
- Product matches require every meaningful term in the same OCR card.
- A reported price must come from that card's `current_price_candidates`.
- The server reconstructs the outbound Coupang answer from structured OCR evidence. Model prose
  cannot add unobserved prices.
- The captured screen is attached as structured reply media when available.

### Every CEO verification request

- Owner directives using 확인, 조회, 검증, 점검, or 알아봐 create a verification run.
- Only a question-relevant evidence tool counts as proof.
- GUI/browser state prefers a captured screen.
- Non-GUI verification uses the strongest available artifact: URL/page ID/message ID/status ID,
  structured tool result, or repository path/line/hash.
- With no successful relevant evidence result, the outbound reply is replaced with
  `증빙 확보 실패`; the requested fact is not presented as confirmed.

### Capture privacy and disposal

- Only regular, single-link `peekaboo_see_<digits>.png` files under the allowed Peekaboo temp,
  cache, or Desktop roots can be attached or cleaned up.
- Symlinks, hard links, arbitrary filenames, and unrelated Desktop images are rejected.
- OCR text is stripped of Discord mention and Markdown injection characters. Prices must match a
  strict Korean-won pattern.
- Evidence state is keyed by `sessionKey + runId`.
- After outbound delivery settles, the generated capture moves to macOS Trash.
- Failed, interrupted, or abandoned delivery receives a five-minute expiry cleanup.
- Cleanup verifies device/inode identity and never performs an unsafe cross-device delete.

## Acceptance criteria

1. The incident phrase routes to Coupang search plus screen inspection.
2. `web_search` is blocked in that turn.
3. Unsupported prices cannot reach the outbound payload.
4. Failed inspection returns the exact safe error and no price.
5. Successful GUI verification attaches at least one valid Peekaboo capture.
6. Delivery completion moves the generated capture to Trash.
7. An unrelated successful tool cannot satisfy a verification request.
8. Pending evidence cannot cross sessions.
9. Local and Mac mini regressions pass.
10. Production Discord replay shows tool trajectory, structured evidence attachment, and
    `deliverySucceeded=true`.

## Operating rule

Codex CLI uses `caveman ultra` unless the CEO disables it. Code-change summaries and verification
evidence remain exact.
