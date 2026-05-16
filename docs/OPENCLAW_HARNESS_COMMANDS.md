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

OpenClaw skill entrypoint:

- `plugins/harness-bridge/skills/harness-control/SKILL.md`

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
