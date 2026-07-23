검토에 필요한 근거를 먼저 수집해, 요청하신 **APPROVE/BLOCK** 판단을 바로 내리겠습니다.

## 1. Objective
Review the repo-root `sys.path` bootstrap in `scripts/openclaw_smartfarm_research_bridge.py` and decide **APPROVE/BLOCK** for non-repo execution safety plus read-only surface integrity.

## 2. Findings
- **Verdict: BLOCK (temporary, verification-gap).**
- **Input artifacts missing:** none (`scripts/openclaw_smartfarm_research_bridge.py` present).
- The change is exactly the expected bootstrap pattern:
  - `import sys`
  - `REPO_ROOT = Path(__file__).resolve().parent.parent`
  - `sys.path.insert(0, str(REPO_ROOT))`
  This should resolve `from scripts.smartfarm_market_research import ...` even when CWD is outside repo.
- Parser/command surface appears unchanged and still read-only (`plan`, `validate`, `search`, `open`, `extract` only; no purchase/cart/order/actuator command added).
- In this session, direct runtime invocation of the script from non-repo CWD could not be executed due environment permission limits, so the first required check was not empirically confirmed.

## 3. Risks
- Without one real execution from a non-repo working directory, import-fix effectiveness remains unproven in the target runtime path.
- `sys.path.insert(0, repo_root)` intentionally prioritizes repo modules; low but real shadowing risk exists if conflicting top-level module names are introduced later.

## 4. Recommended Next Actions
1. On Mac Mini (target context), run: `python3 /path/to/repo/scripts/openclaw_smartfarm_research_bridge.py --help` from a non-repo directory and capture exit/output.
2. Run one functional command similarly (e.g., `plan`) to confirm end-to-end import resolution.
3. If both pass, flip verdict to **APPROVE** with this same safety assessment on read-only surface unchanged.