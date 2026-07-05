# Multi-User SSH Production Safety Runbook

- Version: 0.1
- Date: 2026-07-05
- Scope: Harness production/service servers where multiple people may use SSH and LLM agents for code work
- Related: `docs/governance/DEPLOYMENT_SOURCE_OF_TRUTH.md`, `AGENTS.md`, `CLAUDE.md`
- Status: Red Team reviewed; broad multi-user SSH access is blocked until required enforcement controls are implemented

---

## 1. Objective

Several contributors may soon connect to company service servers over SSH and use LLMs to add features. The risk is not only malicious access. The realistic failure mode is a well-intentioned user asking an LLM to run the wrong command against a live portal, causing downtime, code drift, data loss, or secret exposure.

The operating objective is:

1. No human or LLM should edit live production code directly.
2. No contributor account should have enough permission to stop, overwrite, or redeploy production by accident.
3. Every production change must pass through Git, review, automated checks, and a controlled deploy path.
4. Rollback and service recovery must be faster than manual debugging.
5. LLM work must leave an audit trail: who ran it, where, against which branch, with what deploy evidence.

---

## 2. Non-Negotiable Rules

### Must

- Use `origin/main` as the single source of truth for production code.
- Give each contributor a separate SSH account. Do not share the existing owner account.
- Use per-user workspaces such as `/srv/harness/dev/$USER/harness-platform` or personal machines for development.
- Keep the live production checkout owned by a dedicated service/deploy user.
- Deploy only through an approved deploy script or CI/CD job that pulls from `origin/main`.
- Require pre-deploy checks before restart: tests, build, migration safety check if schema changes, and health check.
- Keep automatic backups before every deploy: code revision, database dump or snapshot, and config snapshot without plaintext secrets.
- Keep a tested rollback command that can restore the previous release without asking an LLM to improvise.
- Log SSH login, sudo, deploy, restart, and LLM-agent command sessions.

### Never

- Do not let normal contributor accounts write to the live production checkout.
- Do not let normal contributor accounts run broad `sudo`, `systemctl restart`, `launchctl bootout`, `docker compose down`, `rm -rf`, `git reset --hard`, or database destructive commands against production.
- Do not deploy by `scp`, manual file copy, editor save inside production, or LLM-generated ad hoc shell commands.
- Do not allow an LLM to read private keys, `.env`, production database dumps, or payment/customer secrets.
- Do not treat "the site works on my SSH session" as production verification.
- Do not bypass Red Team, QA, or legal gates for customer-facing or high-impact changes.
- Do not run heavy builds, dependency installs, load tests, or long-running LLM loops on the production host unless the process is resource-limited and isolated from production services.

---

## 3. Target Architecture

```
Contributor SSH account
  -> personal/dev checkout
  -> feature branch
  -> pull request or reviewed commit
  -> CI checks
  -> protected origin/main
  -> deploy account or CI runner
  -> approved deploy script
  -> production release directory
  -> health check
  -> rollback pointer retained
```

Production should be treated as a release target, not a shared editing machine.

Recommended filesystem shape:

```
/srv/harness/
  prod/
    releases/<git_sha>/
    current -> releases/<git_sha>
    shared/
      .env              # readable only by service/deploy user
      runtime/
      logs/
  dev/
    alice/harness-platform/
    bob/harness-platform/
```

If the current server still uses one mutable checkout, migrate in phases. The first phase can be permission hardening around the existing checkout. The final state should use immutable release directories or an equivalent container image.

---

## 4. SSH Account Model

### Roles

| Role | Login | Permissions |
| --- | --- | --- |
| Contributor | yes | Own dev workspace only; no production write; no production restart |
| Reviewer/Maintainer | yes | Can approve PRs; cannot bypass deploy evidence |
| Deploy user | no interactive login by default | Owns production release path; deploy script only |
| Service user | no interactive login | Runs app process; reads runtime config |
| Break-glass admin | yes, restricted | Emergency only; every use logged and reported |

### Required settings

- `PasswordAuthentication no`
- key-based SSH only
- `PermitRootLogin no`
- no shared private keys
- per-user SSH key rotation and immediate removal on offboarding
- optional: Tailscale/Zero Trust network ACL so SSH is not exposed broadly
- optional: `AllowUsers` or `AllowGroups harness-dev harness-maintainers`

### Sudo policy

Normal contributors should have no general sudo. If they need operational commands, grant only narrow wrappers:

```
%harness-maintainers ALL=(deploy) NOPASSWD: /srv/harness/bin/deploy_harness
%harness-maintainers ALL=(deploy) NOPASSWD: /srv/harness/bin/rollback_harness
%harness-maintainers ALL=(root)   NOPASSWD: /srv/harness/bin/status_harness
```

Do not grant `sudo /bin/bash`, `sudo vim`, `sudo systemctl *`, or wildcard write access to production paths.

Wrapper scripts used from sudoers must be hardened:

- owned by `root:root` or the deploy administrator account,
- not writable by group or world,
- use absolute paths for every command,
- clear or pin environment variables such as `PATH`, `PYTHONPATH`, `NODE_PATH`, `GIT_SSH_COMMAND`, and `DATABASE_URL`,
- reject arbitrary branch/ref/path arguments unless explicitly allowlisted,
- write an audit line for actor, command, arguments, `git_sha`, and result.

---

## 5. Git And Branch Protection

Minimum policy:

- `main` is protected.
- Direct push to `main` is disabled for contributors.
- PR or maintainer-reviewed commit is required.
- Required checks must pass before merge:
  - backend tests relevant to changed code
  - frontend build and lint when frontend changes
  - migration dry-run or explicit migration review when DB schema changes
  - secret scan such as `gitleaks`, GitHub secret scanning, or an equivalent named CI job
  - destructive-command scan for deploy scripts and agent instructions, implemented as a named CI job or pre-merge script
- Signed commits are preferred for maintainers.
- Every deploy records `git_sha`, actor, timestamp, check results, and health-check result.
- Branch protection must include administrators/owners. Maintainers must not be able to bypass checks silently.

For this repo, keep `docs/governance/DEPLOYMENT_SOURCE_OF_TRUTH.md` authoritative: production deployment must flow through `commit -> push -> origin/main -> scripts/deploy_to_macmini.sh` unless a future CI/CD path explicitly replaces it.

---

## 6. LLM Agent Safety Policy

LLM agents may work only in a dev checkout or disposable workspace by default.

Required LLM prompt header for production-adjacent sessions:

```text
You are working in a non-production workspace. Do not edit production checkout,
do not restart services, do not read secrets, do not run destructive commands,
and do not deploy unless an explicit approved deploy task is present.
All production changes must go through Git, review, tests, and the approved deploy script.
```

Production server shell guardrails:

- Put `AGENTS.md` or a local agent policy file in every dev checkout.
- Do not rely on shell aliases as the primary control. Non-interactive SSH and LLM harnesses often bypass shell rc files.
- Enforce risky production operations at the SSH, sudoers, wrapper, or filesystem-permission layer.
- Optional interactive aliases may still make dangerous commands noisy:
  - `rm -rf`
  - `git reset --hard`
  - `git clean -fdx`
  - `docker compose down`
  - service restart commands
  - direct database mutation commands
- Prefer sandboxed agent execution:
  - read-only production context for diagnosis
  - write access only to personal workspace
  - no access to `.env`, SSH keys, database dumps, or payment/customer data
- Save LLM session output or command transcript for any production-adjacent work.

LLM sessions must not receive broad instructions like "fix the server" while attached to production. Use task-scoped language: target branch, allowed files, forbidden commands, verification commands, and deploy authority.

If an LLM must inspect the production host, default to read-only diagnostics:

- no service restart,
- no file writes outside a temporary diagnostics directory,
- no secrets access,
- no database mutation,
- no dependency install,
- no long-running load or build process.

---

## 7. Resource Isolation

Contributor dev workspaces on the production host are a temporary compromise, not the target state. A contributor can cause downtime without touching production files by exhausting CPU, memory, disk, file descriptors, inodes, or shared services.

Required controls before broad access:

- prefer development on local machines, cloud dev environments, or a separate staging host;
- if dev workspaces remain on the production host, enforce CPU/memory/process limits with launchd/systemd/cgroups or equivalent;
- enforce disk quotas for `/srv/harness/dev/$USER`, dependency caches, logs, and temporary directories;
- separate dev database, Redis, Ollama, vector DB, and external API credentials from production;
- prohibit dev migration tests against production DB;
- throttle or block expensive local model jobs on the production host while the portal is serving users.

---

## 8. Deployment Gate

No production deploy is allowed unless this checklist is complete:

1. Branch merged or reviewed commit pushed to `origin/main`.
2. `git status --short` is clean in the source workspace except unrelated files explicitly excluded.
3. Required tests/builds pass.
4. Migration plan is reviewed if database schema or data mutation is involved.
5. Pre-deploy backup/snapshot completed.
6. Deploy script runs from a controlled account.
7. Health check passes:
   - service process up
   - HTTP endpoint returns expected status
   - frontend bundle or API version matches deployed `git_sha`
   - logs have no immediate crash loop
8. Rollback command and previous release pointer are available.
9. Completion report records changed files, commit, deploy command, health-check result, and residual risk.

If any step fails, mark the deploy `blocked` or `residual_risk`; do not call it complete.

Deploy and rollback must be single-flight:

- use a host-level lock such as `flock` around the whole deploy/rollback critical section;
- record the active actor and timestamp in the lock metadata;
- define a stale-lock procedure;
- prevent deploy and rollback from running concurrently.

Deploy must be failure-safe:

- stage a release before touching the live service;
- promote only after build/preflight succeeds;
- if restart or health check fails, the deploy wrapper must automatically roll back to the previous release and report failure;
- a human-run rollback command is not enough for broad multi-user access.

---

## 9. Rollback And Recovery

Every deploy should create a release record:

```json
{
  "service": "harness-platform",
  "git_sha": "abc123",
  "previous_git_sha": "def456",
  "actor": "deploy",
  "deployed_at": "2026-07-05T00:00:00+09:00",
  "backup": "/srv/harness/backups/20260705T000000",
  "health_check": "passed"
}
```

Rollback must be a boring command, not an investigation:

```
/srv/harness/bin/rollback_harness --to previous
```

The rollback script should:

1. switch `current` symlink or checkout to previous release,
2. restore compatible config if needed,
3. restart only the required service,
4. run health check,
5. write a rollback report.

Database rollback is harder than code rollback. For schema changes, require an explicit forward-fix plan or reversible migration before deploy.

---

## 10. Monitoring And Audit

Minimum telemetry:

- uptime check for portal HTTP endpoint
- service process watchdog
- deploy log with actor and `git_sha`
- SSH login log review
- sudo log review
- production dirty-tree drift check
- deploy/rollback lock state
- disk space, memory, CPU, database availability
- alert channel for downtime and failed deploys

Daily automated drift check:

- production tracked files must match `origin/main` or the active deployed `git_sha`
- dirty tracked files in production are a page-worthy incident
- runtime/log/generated files must be outside Git or ignored

---

## 11. Incident Response

Trigger an incident if:

- portal becomes unavailable,
- production checkout has unreviewed tracked-file changes,
- a contributor or LLM ran a forbidden command,
- deploy script bypass was used,
- secret file was exposed to an LLM or copied into logs,
- database destructive command ran outside an approved migration.

Incident steps:

1. Freeze deploys.
2. Preserve logs and LLM transcript.
3. Restore service by rollback or known-good release.
4. Compare production files to `origin/main`.
5. Rotate exposed secrets if any.
6. Record root cause and prevention patch.
7. CEO/President receives a short decision card if user impact, security, or revenue risk exists.

---

## 12. Phased Implementation

### Phase 0 — Same day

- Create separate SSH accounts for every contributor.
- Remove contributor write permission from production checkout.
- Disable direct contributor sudo.
- Announce: no direct production edits, no `scp` deploy, deploy script only.
- Ensure backups exist before the next change window.
- Document emergency rollback command.
- Keep broad multi-user SSH work blocked until deploy locking, auto-rollback, and permission controls are implemented.

### Phase 1 — Within 1 week

- Create `/srv/harness/dev/$USER` workspaces.
- Protect `main` branch and require checks.
- Add named secret scan and destructive-command scan.
- Add deploy wrapper with health check and release log.
- Add deploy/rollback lock.
- Add automatic rollback on failed health check.
- Add production dirty-tree drift alert.
- Add shell/agent policy file to dev checkouts.
- Add resource limits or move dev work off the production host.

### Phase 2 — Within 30 days

- Move production to immutable release directories or containers.
- Make deploy fully non-interactive from CI or deploy account.
- Add automated rollback pointer.
- Add per-deploy DB backup/snapshot.
- Add quarterly access review and key rotation.
- Add tabletop drill: bad LLM command, failed deploy, database migration failure, secret exposure.

---

## 13. Red Team Result

Red Team review was requested for this runbook.

- Claude: reviewed for operational failure modes and missing controls.
- GitHub Copilot CLI: reviewed for engineering gaps and bypass paths.
- Review artifact: `docs/reviews/red_team/MULTI_USER_SSH_PRODUCTION_SAFETY_REVIEW_20260705.md`
- Current verdict: `red_team_block` for broad multi-user SSH access until enforcement controls are implemented.

Required follow-ups before allowing broad multi-user SSH work:

1. Enforce OS permissions and sudoers policy, not only written rules.
2. Protect GitHub `main` and require CI checks.
3. Add production drift alert.
4. Create tested rollback wrapper.
5. Run a tabletop drill before granting broad access.
6. Add deploy/rollback serialization.
7. Add automatic rollback on failed health checks.
8. Enforce resource isolation for dev and LLM workloads.
