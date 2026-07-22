# OpenClaw Status Semantics — Copilot Red Team

- Date: 2026-07-22
- Model: GitHub Copilot CLI
- Mode: independent review
- Final model verdict: `red_team_clear`
- Cross-model verdict: `red_team_residual_risk`

## Findings fixed

1. Generic Harness status could leak into Turtle/unknown-subject answers because old forbidden markers were stale. Golden and unit guards now reject all generic status markers.
2. Overall health could ignore integrity-preflight failures. Status conclusion now includes DB, Ollama, and integrity results.
3. English status bypassed the deterministic evidence brief through the legacy structured bridge. `status` now enters the shared deterministic route.
4. Risk output falsely called disabled capital actions the main constraint even when enabled. Enabled-state regression added.
5. The quality-gate trigger omitted the E2E scorer and corpus paths. Both now trigger the pre-push gate; the gate executes both scorers.
6. Real-entrypoint verification found that an old snapshot could be treated as fresh because evidence time used file-read time. Status evidence now uses payload `generated_at`; stale snapshots fail closed.
7. Copilot found that top-risk wording was inferred as `analysis`, leaving a 24-hour freshness window. All status bridge contracts now force the five-minute status SLA; stale top-risk regression added.

## Final evidence

- Final Copilot verdict: `VERDICT: clear`
- Final session: `70c0cdcc-6b8d-49e4-8f29-97b07429a497`
- Contract safety: 240/240
- Real `run()` E2E golden: 9/9
- Targeted regression suite: 106 passed

## Residual risk

Claude CLI review attempts produced no output and hung. They were terminated. This delta therefore does not claim cross-model `red_team_clear`.
