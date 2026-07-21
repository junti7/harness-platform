#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"

.venv/bin/python scripts/score_openclaw_response_quality.py \
  --corpus configs/openclaw/response_quality_corpus_v1.jsonl \
  --min-cases 240 \
  --output runtime/openclaw_quality_eval.json

.venv/bin/python -m pytest \
  tests/test_openclaw_response_quality.py \
  tests/test_openclaw_agent.py \
  tests/test_slack_listener.py \
  tests/test_openclaw_slack_e2e_probe.py -q

.venv/bin/python scripts/score_openclaw_shadow_quality.py \
  --input runtime/openclaw_verified_delivery_shadow.jsonl \
  --min-days 7 \
  --min-cases 200 \
  --min-family-cases 10 \
  --output runtime/openclaw_shadow_quality.json
