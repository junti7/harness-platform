# Red Team Review: Multi-User SSH Production Safety Runbook

- Date: 2026-07-05
- Artifact reviewed: `docs/operations/MULTI_USER_SSH_PRODUCTION_SAFETY_RUNBOOK.md`
- Review type: Cross-LLM operational Red Team
- Models/resources used:
  - Claude CLI (`claude -p --model sonnet`)
  - GitHub Copilot CLI (`/opt/homebrew/bin/copilot -p`)
- Final verdict: `red_team_block`

Broad multi-user SSH access should remain blocked until the required enforcement controls below are implemented. Claude returned `red_team_clear_with_required_followups`; Copilot returned `red_team_block`. Because the findings describe realistic portal-unavailability paths, the stricter verdict is adopted.

---

## Prompt

```text
You are Red Team reviewer for an operational safety runbook. Review docs/operations/MULTI_USER_SSH_PRODUCTION_SAFETY_RUNBOOK.md in this repository. Do not edit files. Focus on ways multiple SSH users and LLM agents could still make the production portal unavailable despite this runbook. Return: verdict red_team_clear/red_team_block/red_team_clear_with_required_followups; top findings with severity; required fixes; residual risks. Be concise but concrete.
```

---

## Claude Findings

Verdict: `red_team_clear_with_required_followups`

High and medium-high findings:

- Alias-based LLM guardrails do not reliably apply to non-interactive SSH sessions. Full-path commands bypass aliases.
- The runbook lacked deploy locking and automatic rollback on health-check failure.
- Sudo wrapper scripts were not specified as root-owned, non-writable, absolute-path, environment-pinned wrappers.
- Shared production-host dev workspaces can exhaust CPU, memory, disk, or inode resources.
- Dev environments could accidentally share production DB, Ollama, external LLM API keys, or other backing services.
- Branch protection did not explicitly require administrator inclusion.
- Secret scan and destructive-command scan were named as concepts, not actual tools or CI jobs.
- Break-glass admin access needed stronger enforcement and alerting.

Claude required fixes:

- Replace alias-based controls with SSH/sudoers/wrapper/filesystem enforcement.
- Add deploy lock and auto-rollback inside deploy wrapper.
- Harden wrapper ownership, permissions, absolute paths, environment, and arguments.
- Add resource limits or move dev work off production.
- Separate dev backing services from production.
- Include administrators in branch protection.
- Name actual scanning tools/jobs.
- Create the review artifact instead of citing a nonexistent file.

---

## GitHub Copilot Findings

Verdict: `red_team_block`

Critical and high findings:

- No deploy/rollback serialization. Two maintainers or agents can run approved deploy/rollback flows concurrently.
- Approved deploy path is not transactional and did not require mandatory auto-rollback if restart or health checks fail.
- Dev/LLM work remained allowed on the production host without resource isolation, so CPU/RAM/disk/IO exhaustion can still take the portal down.
- LLM guardrails were mostly soft controls: prompt text and aliases are bypassable.
- The runbook referenced wrapper scripts not present in the repo, while the current real path is `scripts/deploy_to_macmini.sh`.

Copilot required fixes:

- Block broad multi-user SSH access until deploys are single-flight.
- Make deploy failure-safe with immutable release/staging and automatic rollback.
- Stop running dev/LLM workloads on production host, or enforce hard limits.
- Replace soft LLM controls with command allowlists, read-only mounts, secret-deny mounts, and no arbitrary production shell.
- Align the runbook with the actual deploy mechanism or implement the wrappers.
- Add migration concurrency control.

---

## Consolidated Required Actions

1. Implement deploy/rollback single-flight locking.
2. Implement automatic rollback when restart, health check, or version verification fails.
3. Harden sudo wrapper scripts before adding `NOPASSWD` permissions.
4. Move dev/LLM workloads off production, or enforce hard resource limits and disk quotas.
5. Separate development backing services from production DB, model services, caches, and secrets.
6. Replace shell-alias LLM controls with enforced command/path/permission controls.
7. Enable branch protection with administrator inclusion.
8. Name and wire concrete secret-scan and destructive-command-scan jobs.
9. Add production drift alert and deploy audit logging.
10. Run a tabletop drill before expanding SSH access.

---

## Residual Risks

- Irreversible database migrations can still cause downtime even with code rollback.
- A sufficiently privileged maintainer can misuse legitimate deploy authority.
- Health checks can miss gray failures; add synthetic end-to-end portal checks.
- Break-glass access remains partially trust-based and must be audited.

