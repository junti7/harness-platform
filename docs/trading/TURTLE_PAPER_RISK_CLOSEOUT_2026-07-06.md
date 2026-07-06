# Turtle Paper Risk Closeout — IBKR and Mac Mini Dirty State

Date: 2026-07-06
Scope: follow-up on the two residual risks from `TURTLE_PAPER_REASSESSMENT_2026-07-06.md`
Status: turtle paper trading blocker reduced; global Mac Mini dirty tree remains a separate repo hygiene item.

## Risk 1 — IBKR Gateway Verification

Status: resolved for paper runtime readiness.

Mac Mini command:

```bash
cd /Users/juntaepark/projects/harness-platform
.venv/bin/python scripts/ibkr_runtime_status.py
```

Observed result:

- IB Gateway paper port `127.0.0.1:4002` connected successfully
- serverVersion: `176`
- account detected: `DUQ416334`
- NAV: `$960,757.53`
- cash: `$810,805.02`
- broker position count: 1
- broker and `docs/reports/ibkr_tws_positions.json` state matched
- SPY historical bars smoke test passed
- script verdict: `ALL CLEAR — B2 실행 준비 완료`

## Risk 2 — Mac Mini Dirty Worktree

Status: turtle-specific blocker closed; global worktree remains intentionally untouched.

The Mac Mini repository has long-running unrelated dirty state from earlier EDU/governance work. A broad reset, full checkout, or stash would risk deleting user/agent work outside this request. Therefore the safe action was scoped:

- verify the 4 turtle closeout files match `origin/main`
- reinstall the actual Mac Mini LaunchAgent plists from the deployed templates
- reload launchd
- verify launchd runtime environment carries the entry lock

Verified target files:

- `harness-os/launchd/com.harness.turtle-auto-trader.plist`
- `harness-os/launchd/com.harness.ibkr-auto-trader.plist`
- `docs/trading/TURTLE_PAPER_REASSESSMENT_2026-07-06.md`
- `docs/reports/completion_evidence/turtle_paper_entry_lock_20260706.json`

All 4 target files had `git diff origin/main -- <path> == 0` on Mac Mini.

Mac Mini LaunchAgent runtime after reinstall/reload:

```text
com.harness.turtle-auto-trader:
  state = not running
  PAPER_TRADING_MAX_POSITIONS => 0
  PAPER_PYRAMID_ENABLED => false
  PAPER_TRADING_AUTO_EXECUTE => false
  runs = 0

com.harness.ibkr-auto-trader:
  state = not running
  PAPER_TRADING_MAX_POSITIONS => 0
  PAPER_PYRAMID_ENABLED => false
  IBKR_TRADING_MODE => paper
  runs = 0
```

## Remaining Repo Hygiene

Do not treat the global Mac Mini dirty tree as fixed.

Current audit showed:

- `HEAD=124ad01`
- `origin/main=07548a2`
- staged paths: 97
- unstaged tracked paths: 25
- untracked paths: 43
- staged-vs-origin differences: 83
- worktree-vs-origin differences: 58

This is outside the turtle paper entry-lock scope and must not be cleaned with `git reset --hard` or broad checkout without a separate owner-approved production cleanup window.

## Operating Decision

For turtle paper trading:

- new Alpaca/IBKR entries remain locked
- pyramiding remains disabled
- existing Alpaca positions remain under broker stop coverage
- IBKR paper runtime is reachable
- Mac Mini installed LaunchAgents now enforce the lock

For global repo hygiene:

- create a separate cleanup task if full Mac Mini worktree reconciliation is required
- use backup + owner-approved scoped file list
- do not erase unrelated dirty files from this turtle closeout
