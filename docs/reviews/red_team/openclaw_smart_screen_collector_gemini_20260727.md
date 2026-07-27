# OpenClaw smart screen collector Red Team — Gemini

Date: 2026-07-27
Reviewer: Antigravity `gemini-3.6-flash-low`
Verdict: `red_team_clear`

Scope:

- `plugins/harness-bridge/index.js`
- `scripts/macos_vision_ocr.swift`
- `tests/test_harness_bridge_plugin.mjs`

Reviewed changes:

- macOS Vision OCR helper for screenshot text extraction.
- Compiled OCR binary cache under repository `scratch/`.
- OCR-derived product/offer, price, and login-clue extraction.
- Bounded automatic scroll collection for Coupang/product/info-collection questions: initial capture, up to two down-scroll captures, best-effort upward restore.
- Coupang search URL routing for owner requests such as `쿠팡에서 생수 검색해서 상품 보여줘`.

Findings:

- `red_team_clear`.
- High-impact browser action gates remain intact for cart, login, checkout, payment, and form actions.
- No click/type/fill/submit actions were introduced.
- Process execution uses array arguments; no shell interpolation.
- Coupang search URLs are built with `new URL()` and `searchParams.set()`.
- OCR image path is restricted to temp, Desktop, and `.peekaboo` screenshot roots.
- Swift OCR helper reads one local image, runs Vision OCR, emits JSON, and performs no network or file writes.
- Scroll loop is bounded to two down-scroll captures with best-effort restore and per-command timeouts.
- Output is capped to avoid context flooding.

Conclusion:

No owner-gating bypass, shell/code injection, path traversal, high-impact browser action leakage, or unsafe scope expansion found.

Final payload hardening review:

- Verdict: `red_team_clear`.
- Added OCR output sanitization, control-character removal, and tighter text/candidate caps.
- Reviewer found no arbitrary code execution, network exfiltration, filesystem abuse, prompt/tool injection, or output-bloat regression.

Final compaction review:

- Verdict: `red_team_clear`.
- Reviewed diff reducing per-page payload for scrolled OCR collection to page index, screenshot path, scroll status, and counts while preserving merged product/price/login candidates.
- Reviewer found the change preserves extraction targets and materially reduces tool result size below the OpenClaw truncation threshold risk.

Exact product-card matching and detail navigation review:

- Verdict: `red_team_clear`.
- Initial review blocked the first grouping window because a wide vertical OCR neighborhood could mix prices from adjacent product cards.
- After tightening the OCR card neighborhood and showing full routing/tool context, reviewer cleared the change.
- Reviewer verified `strict_product_matches` collects product terms and prices only inside the same OCR card neighborhood, and `harness_coupang_product_detail_open` is owner-gated, token-bound, navigation-only, and still excludes login, cart, checkout, payment, purchase, form, shell, Playwright, Browser MCP, and web_fetch paths.
- Follow-up review cleared filtering out top browser/header OCR lines and requiring at least one same-card price before emitting a strict product match, preventing page title or address bar text from becoming clickable product matches.
- Follow-up review cleared current-price extraction for lines containing both total price and unit price, keeping the first price as `current_price_candidates` while retaining all prices in `price_candidates`.
- Price-only detail fallback was initially blocked because arbitrary browser window titles are page-controlled. After restricting title-derived terms to the exact Coupang recommendation title pattern, rejecting URLs/brackets, stripping generic words, requiring at least two terms, and retaining same-card price/click matching, reviewer returned `red_team_clear`.
- Follow-up review cleared preferring Coupang Chrome window-id capture before generic screen analysis for Coupang questions, preventing another frontmost Chrome window such as YouTube from being used as the product-detail source.
- Follow-up review cleared reopening a safe Coupang search URL when a detail target is not found but at least two validated product terms are known, followed by reinspection and the same same-card price/term/click match before one navigation click.
