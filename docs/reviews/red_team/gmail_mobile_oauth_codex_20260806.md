# Gmail mobile OAuth — Codex engineering review

- Order: `gmail-mobile-oauth-20260806`
- Role: implementation owner and deterministic verification; not counted as an independent reviewer
- Input: complete staged diff and live Mac mini `gog` CLI help

## Findings and disposition

- Corrected selected-client verification so auth, Gmail, and Calendar all use `--client mobile`.
- Accepted Gemini's Discord failure finding and made delivery mandatory with three retries.
- Confirmed live `gog v0.19.0` supports `--redirect-uri`, `--remote --step`, and Calendar `--from`.
- Added Uvicorn `--no-access-log` to prevent callback query logging by the application server.
- Kept feature fail-closed until a Google Web OAuth client with the exact Tailnet HTTPS redirect URI is installed.

Verdict: engineering checks clear; production end-to-end remains blocked on the one-time Google Web OAuth client configuration.
