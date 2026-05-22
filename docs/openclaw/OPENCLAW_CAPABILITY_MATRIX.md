# OpenClaw Capability Matrix

Status date: 2026-05-22

This file separates three states that must not be conflated:

- `gateway skill ready`: OpenClaw gateway can see the skill.
- `runtime authenticated`: the underlying CLI/API has usable credentials in non-interactive runtime.
- `Harness Slack adapter exposed`: `adapters/content/openclaw_agent.py` exposes a safe tool path from Slack.

## Current Runtime Snapshot

- Gateway ready/visible skills: 41
- Missing-requirement skills: 11
- Harness Slack adapter direct tools: `read_file`, `list_files`, `web_search`, `browser_research`, `coupang_product_search`, `fetch_url`, `gmail_search`, `gmail_create_draft`, `gmail_update_draft`, `gmail_send`, `gmail_trash`, `gmail_modify_labels`, `write_file`, `run_script`, `send_slack`, `render_pdf`

## Slack Adapter Rule

OpenClaw must not answer "yes, I can use it" from installation status alone.

Correct answer shape:

1. Gateway skill status
2. Runtime auth/setup status when known
3. Slack adapter exposure
4. Safety boundary and approval requirement

## Ready Gateway Skills

`1password`, `apple-notes`, `apple-reminders`, `bear-notes`, `blogwatcher`, `blucli`, `camsnap`, `coding-agent`, `eightctl`, `gemini`, `gh-issues`, `gifgrep`, `github`, `gog`, `harness-control`, `healthcheck`, `himalaya`, `imsg`, `model-usage`, `nano-pdf`, `node-connect`, `notion`, `obsidian`, `openai-whisper`, `openhue`, `ordercli`, `peekaboo`, `session-logs`, `skill-creator`, `slack`, `songsee`, `sonoscli`, `summarize`, `taskflow`, `taskflow-inbox-triage`, `things-mac`, `tmux`, `video-frames`, `wacli`, `weather`, `xurl`

## Missing Requirements

`clawhub`, `discord`, `goplaces`, `mcporter`, `openai-whisper-api`, `oracle`, `sag`, `sherpa-onnx-tts`, `spotify-player`, `trello`, `voice-call`

## Important Cases

### Gmail / Google Workspace (`gog`)

- Gateway: ready/visible
- Slack adapter: partial, `gmail_search`, `gmail_create_draft`, `gmail_update_draft`, `gmail_send`, `gmail_trash`, `gmail_modify_labels`
- Runtime auth: account entry exists, but file keyring requires `GOG_KEYRING_PASSWORD` in non-interactive runtime unless switched to macOS Keychain
- Allowed from Slack: Gmail search/read, draft create/update, send, trash, label modify
- Mutation gate: send/trash/label/draft mutation requires CEO identity and `OPENCLAW_GMAIL_MUTATION_ENABLED=true`
- OAuth scope note: if the current token was created with read-only Gmail scope, re-auth with full Gmail scope is required for send/delete/modify.

### Notion

- Gateway: ready/visible
- Slack adapter: bridge/script path only
- Allowed from Slack: approved archive/ops scripts
- Not exposed: arbitrary Notion database mutation

### Slack

- Gateway: ready/visible
- Slack adapter: partial, `send_slack`
- Required: CEO identification + preflight because external message sending has external effect

### General Web Search

- Gateway: no dedicated generic search skill required
- Slack adapter: `web_search` exposed
- Runtime provider: `OPENCLAW_WEB_SEARCH_PROVIDER=auto`; uses Brave Search when `BRAVE_SEARCH_API_KEY` is configured, otherwise falls back to DuckDuckGo HTML search
- Allowed from Slack: read-only keyword search returning title/URL/snippet
- Boundary: use `fetch_url` for deeper reading of a specific result; do not treat snippets as verified facts

### Read-only Browser Research

- Gateway: no dedicated gateway skill required
- Slack adapter: `browser_research` exposed
- Runtime provider: Playwright Chromium in the Harness venv
- Allowed from Slack: public-page browsing, rendered-page reading, public search, read-only comparison, shopping price research when the target site allows automated access
- Explicitly blocked: login, signup, address entry, cart, order, purchase, payment, coupon application, form submission, or any remote state-changing action
- Coupang note: direct headless browser access currently returns `Access Denied`; OpenClaw must report this limitation instead of inventing prices. Use an official/affiliate API, user-provided page content, or general web/price-search fallback for Coupang-like tasks.

### Coupang Partners/Open API

- Gateway: no dedicated gateway skill required
- Slack adapter: `coupang_product_search` exposed
- Runtime auth: requires `COUPANG_PARTNERS_ACCESS_KEY` and `COUPANG_PARTNERS_SECRET_KEY`
- Default path: `COUPANG_PARTNERS_PRODUCT_SEARCH_PATH=/v2/providers/affiliate_open_api/apis/openapi/v1/products/search`
- Allowed from Slack: read-only keyword product search
- Explicitly blocked: order, purchase, cart, login, address entry, payment
- Boundary: if keys are missing or API access is not granted by Coupang, OpenClaw must report the setup gap instead of fabricating product prices.

### 1Password

- Gateway: ready/visible
- Slack adapter: not exposed
- Reason: secret access must not be exposed through general Slack chat

### iMessage / X / GitHub / Gemini / Himalaya

- Gateway: ready/visible
- Slack adapter: not exposed unless a specific bridge or tool is later implemented
- Correct answer: "OpenClaw gateway has the skill, but this Slack adapter cannot directly execute it yet."

## Failure Memory

Failure pattern:

- User asks: "Can you read Gmail?"
- Wrong answer: "No, policy prevents access."
- Correct answer: "Gateway has `gog`; Slack adapter has Gmail tools; execution requires runtime OAuth/keyring readiness, CEO preflight, and mutation flag for write/send/delete."
