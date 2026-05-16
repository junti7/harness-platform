---
name: harness-control
description: Operate the Harness 24/7 control plane through the local OpenClaw-to-Codex bridge.
user-invocable: true
---

# Harness Control

Use this skill when operating the `harness-platform` control plane from OpenClaw on the 24/7 host.

## Purpose

This skill maps OpenClaw operator intent to the local bridge entrypoint:

- `~/projects/harness-platform/scripts/openclaw_codex_bridge.py`

All commands must run from:

- `~/projects/harness-platform`

Python runtime:

- `~/projects/harness-platform/.venv/bin/python`

## Core Commands

### 1. System status

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py status --format json
```

Use for:

- bridge health
- OpenClaw / Ollama / Postgres readiness
- Slack / Notion secret presence

### 2. Build a decision card

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py decision-card signal 1 --format json
```

Supported target types:

- `signal`
- `refined_output`
- `research_report`

Formats:

- `text`
- `json`
- `slack-json`

### 3. Record a President decision

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py record-decision signal 1 approved signal_approve --reason "mobile approve"
```

Important:

- use canonical approval types only
- do not use `capital_action_approve` unless `CAPITAL_ACTIONS_ENABLED=true`

### 4. Send an ops note to Slack

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py route-note agent_openclaw_routing "OpenClaw task started"
```

Common routes:

- `agent_openclaw_routing`
- `exec_president_decisions`
- `ops_incidents`

### 5. Build a task packet for handoff

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py task-packet research "Competitor refresh" \
  --objective "Collect updated competitor report signals" \
  --input-artifact docs/library/competitor_intelligence/index.md \
  --output-artifact docs/reports/competitor_refresh.md \
  --route agent_openclaw_routing
```

Use for:

- handing work to another model
- preserving input/output/checklist context

### 6. Run the pipeline

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py run-pipeline --notify-slack
```

Use only when:

- scheduled run failed
- manual refresh is explicitly requested

### 7. Publish a daily ops brief

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py publish-ops-brief --to-slack --to-notion --route exec_daily_brief
```

Use for:

- daily executive operations summary
- Notion archive of control-plane health
- `agent_reviews` logging of OpenClaw ops checks

### 8. Push an approval card

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py push-approval-card research_report 7 --route exec_president_decisions
```

Use for:

- representative mobile approval surface
- explicit executive review routing

### 9. Dispatch a task packet to external LLM CLIs

```bash
cd ~/projects/harness-platform
.venv/bin/python scripts/openclaw_codex_bridge.py dispatch-task-packet benchmark "Competitor report benchmark" \
  --objective "Compare premium AI/tech intelligence products and summarize monetizable gaps" \
  --input-artifact docs/COMPETITIVE_LANDSCAPE.md \
  --provider gemini \
  --provider copilot
```

Use for:

- Claude / Gemini / Copilot parallel handoff
- packetized cross-review with saved outputs under `docs/reports/llm_outputs`

## Operator Rules

1. Do not bypass the bridge and write approvals directly.
2. Do not reinterpret approval semantics.
3. Use Slack route names, not raw channel ids, for routine operations.
4. High-impact publish/investment decisions still require Legal, Red Team, QA, and President approval gates.
5. If the bridge status is degraded, post an ops note first and then investigate.
