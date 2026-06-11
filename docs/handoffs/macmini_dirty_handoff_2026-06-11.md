# Mac Mini Dirty Handoff — 2026-06-11

## Summary

- MBP local dirty item `data/edu_research/evidence_bank.json` was a runtime timestamp-only drift and was reverted locally.
- Edu chat transcript export / RED TEAM UX changes were committed and pushed to `origin/main`.
- Those changes were selectively deployed to Mac Mini and the Mac Mini frontend was rebuilt successfully.
- Mac Mini worktree is still dirty, but the remaining dirty state is **not** limited to the edu chat work. It includes many older tracked modifications, additions, and untracked files that should not be force-cleaned blindly.

## Completed Today

### 1. Edu chat commits pushed to SoT

- `7a53f2c` `Add edu transcript export and red team review UX`
- `6206867` `Improve edu chat mobile action visibility`
- `d7f27a2` `Show edu export actions before chat starts`

### 2. Mac Mini selective deploy completed

Deployed paths:

- `harness-os/backend/main.py`
- `harness-os/frontend/src/pages/EduPilotPage.tsx`
- `harness-os/frontend/public/edu-pilot-app.html`

Verification:

- selective checkout from `origin/main` completed with diff `0` for all three paths
- Mac Mini frontend build completed at `2026-06-11 10:14`
- Mac Mini backend health responded `{"ok":true,...}`
- built frontend bundle contains `RED TEAM`, `Markdown`, and `transcript 저장` strings

## Local MBP Status

- local repo is now clean after reverting the timestamp-only drift in `data/edu_research/evidence_bank.json`

## Mac Mini Status

### Important distinction

Mac Mini is **service-updated** for the edu chat feature, but the Mac Mini git worktree is **not clean**.

- Mac Mini HEAD observed during verification: `010fa02`
- `origin/main` observed during verification: `d7f27a2`

This means Mac Mini still carries older working-tree deltas relative to its local HEAD and is not yet globally normalized to `origin/main`.

### Current dirty categories on Mac Mini

#### A. Tracked product/code/config changes already present before this cleanup

Examples:

- `harness-os/backend/main.py`
- `harness-os/frontend/src/pages/EduPilotPage.tsx`
- `harness-os/frontend/public/edu-pilot-app.html`
- `core/trading_universe.py`
- `scripts/pipeline_watchdog.py`
- `scripts/start_ibgateway_ibc.sh`
- `run_pipeline.py`
- multiple `configs/trading/*`, `scripts/*`, `docs/*`

Interpretation:

- these are not safe to discard blindly
- some likely represent older prod-only or partially deployed work
- some may be staged deltas caused by selective checkout against an older local HEAD

#### B. Runtime/report churn

Examples:

- `data/edu_research/evidence_bank.json`
- `docs/reports/ar_tracker.jsonl`
- `docs/reports/gate_tracker.jsonl`
- `docs/reports/investment_signal_candidates*.json*`
- `docs/operations/APPROVAL_REQUESTS.json`

Interpretation:

- mostly operational outputs or semi-runtime artifacts
- these should be separated from true code drift

#### C. Untracked files

Examples:

- `.env.bak_20260610_univ`
- `docs/reports/WBR-2026-06-05.md`
- `docs/reports/price_feed_audit.txt`
- `logs/slack_listener.log.1`
- `tests/test_trading_universe.py`

Interpretation:

- mixed bag of backup, report, log, and possible real source file
- especially `tests/test_trading_universe.py` must be reviewed before deletion

## Why I Did Not Force-Clean Mac Mini

Force-cleaning Mac Mini now would be unsafe because:

- the dirty set is broad and predates the edu chat change
- some files are likely valuable source changes, not disposable runtime noise
- repo policy and deployment SoT explicitly forbid unsafe destructive normalization on the prod machine

## Recommended Next Steps

### Safe path

1. Snapshot Mac Mini dirty state into an artifact.
2. Split files into:
   - runtime-only / ignorable
   - valuable source changes that must be moved to MBP and committed
   - stale backups/logs safe to archive or remove
3. Normalize Mac Mini only after those categories are resolved.

### Highest-priority review set

Review first because they directly affect product/runtime behavior:

- `harness-os/backend/main.py`
- `harness-os/frontend/src/pages/EduPilotPage.tsx`
- `harness-os/frontend/public/edu-pilot-app.html`
- `core/trading_universe.py`
- `scripts/pipeline_watchdog.py`
- `scripts/start_ibgateway_ibc.sh`
- `scripts/ibkr_tws_paper_trader.py`
- `scripts/turtle_auto_trader.py`
- `run_pipeline.py`

### Likely cleanup candidates after review

- log/report churn under `docs/reports/`
- runtime timestamp drift in `data/edu_research/evidence_bank.json`
- backup/log leftovers such as `.env.bak_20260610_univ`, `logs/slack_listener.log.1`

## Operational Conclusion

- The edu chat transcript export and RED TEAM UX is deployed on Mac Mini service runtime.
- Mac Mini git cleanliness remains an open operational issue and needs a dedicated cleanup pass, not an ad hoc force reset.
