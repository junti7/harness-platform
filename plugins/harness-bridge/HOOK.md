# Harness Bridge — Hook Manifest

This plugin registers scoped routing and enforcement hooks. Other Harness
control-plane operations remain operator-triggered through `harness-control`.

## Registered Hooks

- `before_prompt_build`: injects the Saju bridge routing invariant only for
  direct Saju requests and contextual follow-ups.
- `before_tool_call`: during a Saju turn, blocks shell use of `nlm` and all
  structured NotebookLM query/chat tools. Outside a Saju turn it blocks only
  literal `nlm` commands or structured queries that also name the fixed Saju
  notebook. Run markers are keyed to OpenClaw run/session identifiers, capped,
  expired after ten minutes, and cleared by `agent_end`.

## Entry Points

- Skill: `skills/harness-control/SKILL.md`
- Bridge: `~/projects/harness-platform/scripts/openclaw_codex_bridge.py`

## Usage

Invoke the `harness-control` skill or run bridge commands via the terminal.
See `SKILL.md` for the full command reference.
