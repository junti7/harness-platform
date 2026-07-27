# OpenClaw smart screen collector Red Team — Claude

Date: 2026-07-27
Reviewer: Antigravity `claude-sonnet-4-6`
Verdict: `red_team_clear`

Scope:

- `plugins/harness-bridge/index.js`
- `scripts/macos_vision_ocr.swift`
- `tests/test_harness_bridge_plugin.mjs`

Reviewed changes:

- macOS Vision OCR helper for screenshot text extraction.
- Compiled OCR binary cache under repository `scratch/`.
- OCR-derived product/offer, price, and login-clue extraction.
- Bounded automatic scroll collection for Coupang/product/info-collection questions.
- Coupang search URL routing followed by screen-inspect/OCR/scroll collection.

Findings:

- `red_team_clear`.
- Owner gates and high-impact browser action blocks remain intact.
- No injection vectors found; process execution uses array-form args and search query is URL-encoded.
- Swift helper is minimal: local image read, Vision OCR, JSON stdout; no network/write/dynamic loading behavior.
- Read-only boundary is preserved except bounded scroll-position side effect, which is explicitly limited and restored best-effort.
- Path-prefix guard was added for OCR image inputs.

Conclusion:

No blocking safety regression found.
