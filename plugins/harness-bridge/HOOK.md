# Harness Bridge — Hook Manifest

This plugin registers no automatic event hooks.

All Harness control-plane operations are invoked explicitly via the
`harness-control` skill or by running bridge commands directly.

## Registered Hooks

None. Operator-triggered only.

## Entry Points

- Skill: `skills/harness-control/SKILL.md`
- Bridge: `~/projects/harness-platform/scripts/openclaw_codex_bridge.py`

## Usage

Invoke the `harness-control` skill or run bridge commands via the terminal.
See `SKILL.md` for the full command reference.
