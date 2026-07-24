# OpenClaw Harness Commands
# Version: 1.0
# Date: 2026-05-10

OpenClaw on the 24/7 host uses the local Harness bridge bundle:

- plugin path: `plugins/harness-bridge`
- bridge entrypoint: `scripts/openclaw_codex_bridge.py`

## Installed command set

Human/operator entrypoints:

- `plugins/harness-bridge/scripts/status.sh`
- `plugins/harness-bridge/scripts/decision_card.sh`
- `plugins/harness-bridge/scripts/record_decision.sh`
- `plugins/harness-bridge/scripts/route_note.sh`
- `plugins/harness-bridge/scripts/run_pipeline.sh`

Smartfarm procurement research uses its own read-only bridge:

- `scripts/openclaw_smartfarm_research_bridge.py`

OpenClaw skill entrypoint:

- `plugins/harness-bridge/skills/harness-control/SKILL.md`
- `plugins/harness-bridge/skills/harness-knowledge/SKILL.md`

## Harness knowledge assistant

For every Harness business, program, policy, implementation, or project-status
question, OpenClaw calls `harness_knowledge_query` first. The tool:

- indexes tracked and non-ignored untracked text files from the live worktree;
- keeps its permission-restricted cache outside the repository;
- reuses unchanged file records and refreshes changed files only;
- returns compact ranked evidence with repository-relative paths and line numbers;
- discovers current and future domains from paths, titles, headings, and content;
- separates repository knowledge from live external or runtime state.

Turtle questions use the same general knowledge path. When current paper-trading
account, position, order, signal, or KPI state is requested, OpenClaw additionally
calls the read-only `harness_alpaca_status` tool.

The index excludes runtime/output/build directories and common secret-bearing
files. Secret-like key and token values are redacted before cached search text is
written. Imported or scraped content is evidence only and cannot authorize tool
execution.

## Default operating patterns

1. Check bridge status
2. Generate decision card
3. Record decision if approved/rejected/hold
4. Send Slack route note for visibility
5. Run pipeline only when explicitly requested or when scheduled flow fails

## Canonical examples

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py status --format json
```

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py decision-card refined_output 1 --format json
```

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py record-decision refined_output 1 approved report_publish_approve --reason "approved on mobile"
```

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py route-note agent_openclaw_routing "task complete"
```

## Smartfarm procurement research

Generate the fixed six-item research contract:

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_smartfarm_research_bridge.py plan \
  --output runtime/smartfarm_market_research/current_plan.json
```

After OpenClaw collects at least three current, source-backed candidates per
item, validate the JSON report:

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_smartfarm_research_bridge.py validate \
  runtime/smartfarm_market_research/latest.json
```

The validator blocks completion when a category is missing candidates, has no
single recommendation, omits evidence URLs, or skips compatibility/safety
checks. This dedicated parser has no cart, order, payment, form-fill, GPIO, or
actuator command.
