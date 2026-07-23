# Smartfarm Remote Import Bootstrap Review

## 1. Objective
Verify that the 4-line repo-root `sys.path` bootstrap added to `scripts/openclaw_smartfarm_research_bridge.py` (after Mac Mini hit `ModuleNotFoundError`) safely enables execution from non-repo working directories **without** weakening the read-only parser or procurement safety. Return APPROVE or BLOCK.

Input artifact present: ✅ `scripts/openclaw_smartfarm_research_bridge.py`.

## 2. Findings
- **Diff scope** — `git diff` confirms the change is *only* the additive bootstrap: `import sys`, `REPO_ROOT = Path(__file__).resolve().parent.parent`, `sys.path.insert(0, str(REPO_ROOT))`. No command, argument, or handler was touched or removed.
- **Fix correctness** — `Path(__file__).resolve()` yields an absolute path, so `REPO_ROOT` is cwd-independent; the insert runs before the `scripts.smartfarm_market_research` import. Verified by executing `... plan` (exit 0, full valid JSON plan emitted). `scripts/` has no `__init__.py` but resolves as a namespace package once REPO_ROOT is on `sys.path`, so the import succeeds. This is the correct, minimal fix for the ModuleNotFoundError.
- **Ordering is safe** — All stdlib imports (`argparse`, `json`, `sys`, `pathlib`, `typing`) occur *before* line 12, so they are already resolved and cannot be shadowed by the newly-prepended repo root. Lazy imports inside `command_search/open/extract` (`adapters.content.tools`, `scripts.browser_control`) are intended repo modules.
- **Read-only surface unchanged** — Parser still exposes only `plan/validate/search/open/extract`. Description still declares "no form-fill, cart, order, payment, GPIO, or actuator command." `candidate_contract.rules` retains "Do not add to cart, place an order, or spend money" and `decision: shortlist_only_no_purchase`. Procurement/actuator safety intact.

## 3. Risks
- **Minor (non-blocking):** `sys.path.insert(0, ...)` prepends repo root at highest priority. If any repo top-level directory ever collides with an installed third-party package name, the repo copy would shadow it for *lazily* imported modules. No collision exists today; `insert(0)` is the standard repo-bootstrap idiom. Could use `append` for extra defensiveness, but not required.
- Repeated invocations add duplicate `sys.path` entries — negligible, no correctness impact.
- **Governance note:** This is a single-specialist (claude) verdict. Per CLAUDE.md/LLM_GROUND_RULES, a formal `red_team_clear` token requires an explicit CEO red-team order plus two independent model artifacts — neither is asserted here, so I do **not** emit `red_team_clear`.

## 4. Recommended Next Actions
- **APPROVE** — the bootstrap safely fixes remote/non-repo execution and leaves the read-only command surface and procurement guards unchanged.
- Optional hardening (low priority): guard against duplicate insertion, e.g. `if str(REPO_ROOT) not in sys.path:` — cosmetic, not required for approval.
- Deploy via `scripts/deploy_to_macmini.sh` only (no manual Mac Mini edit), then confirm the original `... plan`/`validate` invocation runs clean from the Mac Mini working directory and verify `git status` is clean on both MBP and Mac Mini before closing.

**Verdict: APPROVE** (single-specialist; not a two-model `red_team_clear`).