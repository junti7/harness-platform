#!/bin/sh
set -eu
cd "$HOME/projects/harness-platform"
.venv/bin/python scripts/openclaw_codex_bridge.py status --format json
