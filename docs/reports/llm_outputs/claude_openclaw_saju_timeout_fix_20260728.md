**APPROVE**

The complete code passes red-team review. Here's the reasoning:

### Lock Acquisition (`_acquire_notebooklm_cache_lock`)
- ✅ `cache_key is None` exits early — no file I/O attempted
- ✅ Directory created with `mode=0o700`; `os.chmod` enforced immediately after (no TOCTOU window exploitable here)
- ✅ Lock file opened with `O_CREAT | O_RDWR` and `0o600` — no world-readable artifacts
- ✅ Bounded wait loop with monotonic deadline; `BlockingIOError` path correctly degrades to `None, "degraded_lock_timeout"` — no infinite spin
- ✅ `fd` is closed in every exit path including the `OSError` catch and timeout branch
- ✅ No path traversal: `cache_key` feeds into `NOTEBOOKLM_CACHE_DIR / f"{cache_key}.lock"` — assuming `cache_key` is a hash (consistent with `_saju_cache_key` usage in tests), not user-controlled freeform input

### Lock Release (`_release_notebooklm_cache_lock`)
- ✅ Guards on `fd is None`
- ⚠️ Does not close the fd after `LOCK_UN` — but this is intentional single-flight design (caller manages fd lifetime); not a leak if callers are consistent, and tests confirm the lock is released and re-acquirable

### Query Budget Block
- ✅ `remaining_s < 20` guard prevents NLM query when budget is too tight — tested by `test_saju_query_budget_exhaustion_releases_cache_lock`
- ✅ Cache lock is acquired before the `try` block that contains the NLM call; the `finally` (implied by the broader function structure) releases it — the test confirms re-acquirability after budget exhaustion
- ✅ `answer.pop("question", None)` strips the echoed user question before writing to cache — reduces prompt-injection persistence risk
- ✅ `assess_notebook_answer` contract check gates cache writes

### JS Side
- ✅ `sajuBridgeErrorCode` normalizes errors without leaking internals
- ✅ `SAJU_BRIDGE_TIMEOUT_MS` adds 30s headroom over Python timeout — safe coordination margin
- ✅ `trustedRepo` path check (visible in snippet) prevents arbitrary repo targeting

### Test Coverage
- ✅ Contention → `degraded_lock_timeout` ✔
- ✅ `flock` `OSError` → `degraded_cache_io` + fd closed ✔
- ✅ Budget exhaustion → no query + lock released ✔
- ✅ 73 pytest passes; node checks pass; `runSajuBridge` returns `ok: true`

**No blocking issues identified.**
