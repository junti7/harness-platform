# Mac Mini Dirty Cleanup — 2026-07-06

Date: 2026-07-06
Host: Mac Mini (`macmini`)
Repo: `/Users/juntaepark/projects/harness-platform`
Scope: full Mac Mini worktree dirty cleanup after turtle paper trading closeout
Status: complete

## Before Cleanup

Mac Mini repository state before cleanup:

- `HEAD=124ad01`
- `origin/main=ce8511d`
- dirty entries: `167`

The dirty tree mixed staged changes, unstaged changes, and untracked files from earlier EDU/governance/trading work. Because the user explicitly requested full dirty cleanup, the worktree was cleaned to `origin/main`, but only after preserving a recovery copy.

## Backup

Backup directory on Mac Mini:

```text
scratch/dirty_cleanup_20260706_094021
```

Backup artifacts:

- `status_short_before.txt`
- `status_porcelain_before.txt`
- `worktree.diff`
- `index.diff`
- `untracked_files.txt`
- `untracked_files.tar.gz`
- `stash_output.txt`
- `stash_list_after.txt`
- `reset_output.txt`
- `clean_output.txt`

Git stash:

```text
stash@{0}: On main: macmini full dirty cleanup backup 20260706_094021
```

The stash includes tracked and untracked changes (`git stash push --include-untracked`).

## Cleanup Command Path

The cleanup used:

```bash
git stash push --include-untracked -m "macmini full dirty cleanup backup 20260706_094021"
git fetch origin -q
git reset --hard origin/main
git clean -fd
```

This was intentionally done only after backup because it changes the worktree globally.

## After Cleanup

Mac Mini state after cleanup:

- `HEAD=ce8511d`
- `origin/main=ce8511d`
- `git status --short` count: `0`

## Runtime Verification

Backend smoke:

```text
backend_http=200 time=0.004656
```

Frontend smoke:

```text
frontend_http=200 time=0.087286
```

IBKR paper runtime:

- Gateway connected on paper port `4002`
- account: `DUQ416334`
- NAV: `$961,764.90`
- broker/state position match: pass
- SPY bars smoke: pass
- verdict: `ALL CLEAR — B2 실행 준비 완료`

Turtle/IBKR paper LaunchAgent entry lock:

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

## Recovery

If any of the cleaned Mac Mini dirty work is needed later:

1. Inspect the backup files under `scratch/dirty_cleanup_20260706_094021`.
2. Prefer reading `status_short_before.txt`, `index.diff`, `worktree.diff`, and `untracked_files.txt` first.
3. Restore specific files from `untracked_files.tar.gz` or apply small hunks manually.
4. Use `git stash show --stat stash@{0}` and `git stash show -p stash@{0}` before any stash apply.
5. Do not blindly run `git stash pop`; apply only scoped files/hunks.

## Closeout

The previous global Mac Mini dirty-tree residual risk is closed:

- worktree clean
- origin/main aligned
- runtime services reachable
- trading entry lock preserved
- recovery artifact available
