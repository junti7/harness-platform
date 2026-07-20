# Copilot Red Team: OpenClaw Gmail Brief

- Date: 2026-07-20
- Model: GitHub Copilot CLI
- Verdict: `red_team_residual_risk`

## Findings

1. Gmail `after:` / `before:` date-only syntax can use a non-KST boundary.
2. Raw Gmail error payloads may leak internal metadata if sent to Slack.
3. Excluding excerpts from session persistence does not by itself prove no operational data retention in Slack delivery/runtime paths.

## Disposition

- KST requests now query a bounded wider window and filter returned item timestamps in Asia/Seoul before selecting messages.
- User-facing Gmail query errors are normalized; raw bridge errors are not included in Slack response text.
- Remaining residual risk is production Slack path verification after targeted deployment.
