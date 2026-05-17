# Harness LLM Handoff
# Date: 2026-05-17

This file is a temporary handoff for another LLM to continue the work without losing context.

## What this repo is doing

Harness is not an article-summary app. It is a Physical AI / AGI creator subscription operating system built around:

- weekly issue production
- free subscriber growth
- paid conversion
- multi-LLM review gates
- goal-oriented closed loops
- long-term company memory in Notion

## Current policy decisions already in place

- `red-team` default is `Claude + Gemini + Codex`
- pass rule is `2-of-3 approve/clear`
- non-negotiable findings still block majority override
- `/goal` is a durable closed-loop system, not a wrapper around one LLM feature
- `Business Operations Team` owns forecasting, anomaly detection, root-cause diagnosis, and escalation thresholds
- strategy and forecasting must be based on explicit mathematical models
- Substack is a pilot adapter for the goal loop, not the canonical goal itself
- Notion is the long-term company archive / record vault

## Implemented so far

### Goal loop

Files:

- [docs/GOAL_LOOP_ARCHITECTURE.md](/Users/juntae.park/projects/harness-platform/docs/GOAL_LOOP_ARCHITECTURE.md)
- [docs/openclaw/GOAL_COMMAND_SURFACE.md](/Users/juntae.park/projects/harness-platform/docs/openclaw/GOAL_COMMAND_SURFACE.md)
- [infra/migrations/2026-05-17_goal_loop.sql](/Users/juntae.park/projects/harness-platform/infra/migrations/2026-05-17_goal_loop.sql)
- [scripts/goal_loop.py](/Users/juntae.park/projects/harness-platform/scripts/goal_loop.py)
- [scripts/openclaw_codex_bridge.py](/Users/juntae.park/projects/harness-platform/scripts/openclaw_codex_bridge.py)
- [adapters/content/openclaw_agent.py](/Users/juntae.park/projects/harness-platform/adapters/content/openclaw_agent.py)

Status:

- DB migration applied to `harness_dev`
- smoke test passed for:
  - `goal-create`
  - `goal-model`
  - `goal-snapshot`
  - `goal-diagnose`
  - `goal-status`
- generic provider snapshot API added:
  - `goal-provider-snapshot`
- Substack-specific snapshot remains as a pilot adapter:
  - `goal-substack-snapshot`

### Substack

Files:

- [docs/operations/SUBSTACK_SYSTEM_PLAYBOOK.md](/Users/juntae.park/projects/harness-platform/docs/operations/SUBSTACK_SYSTEM_PLAYBOOK.md)
- [docs/MONETIZATION_STRATEGY.md](/Users/juntae.park/projects/harness-platform/docs/MONETIZATION_STRATEGY.md)
- [docs/MARKETING_STRATEGY.md](/Users/juntae.park/projects/harness-platform/docs/MARKETING_STRATEGY.md)

Status:

- Substack is the primary publication/growth system for Phase 1
- The goal architecture was generalized so Substack is only one provider adapter

### Notion archive

Files:

- [docs/operations/NOTION_OPERATING_SYSTEM.md](/Users/juntae.park/projects/harness-platform/docs/operations/NOTION_OPERATING_SYSTEM.md)
- [docs/operations/NOTION_ARCHIVE_ARCHITECTURE.md](/Users/juntae.park/projects/harness-platform/docs/operations/NOTION_ARCHIVE_ARCHITECTURE.md)
- [scripts/notion_audit.py](/Users/juntae.park/projects/harness-platform/scripts/notion_audit.py)
- [scripts/notion_apply_archive_schema.py](/Users/juntae.park/projects/harness-platform/scripts/notion_apply_archive_schema.py)
- [scripts/notion_archive_entry.py](/Users/juntae.park/projects/harness-platform/scripts/notion_archive_entry.py)
- [scripts/send_notion_archive.py](/Users/juntae.park/projects/harness-platform/scripts/send_notion_archive.py)
- [adapters/content/publisher.py](/Users/juntae.park/projects/harness-platform/adapters/content/publisher.py)

Current Notion DB status:

- existing DB was audited
- current DB originally had only:
  - `제목`
  - `본문`
  - `태그`
  - `소스`
  - `발행일`
- schema was expanded live with archive-oriented properties:
  - `Artifact Type`
  - `Team`
  - `Project`
  - `Goal ID`
  - `Goal Metric`
  - `Project Status`
  - `Outcome`
  - `Source Channel`
  - `Event Date`
  - `Last Reviewed`
  - `Reminder Date`
  - `Canonical Key`
  - `Summary`
  - `Decision Summary`
  - `Action Items`
  - `Lessons Learned`
  - `Failure Pattern`
  - `Parent Ref`
  - `DB Record Ref`
  - `URL`
  - `LLM Ready`
  - `Historical Value`
  - `Confidentiality`

## Red-team result on Notion structure

The red-team finding was:

- schema expansion is good
- but legacy publisher still only writes the 5 original fields
- lineage is still too text-heavy
- required metadata is not yet enforced in the actual writer path
- there is no reminder/retrieval loop yet

So the Notion system is improved, but not yet fully “company history archive grade”.

## Important caveats

- Do not reveal secrets from `.env`
- Do not assume `goal-substack-snapshot` is the final goal surface
- Do not keep adding provider-specific logic directly into the goal core
- The next step is provider-agnostic registry + stronger Notion archiving discipline

## Best next steps

1. Add a provider adapter registry for the goal loop so `substack` stays a plugin, not a special case
2. Update the archive writer path so every internal artifact can populate the new Notion properties
3. Add a reminder / re-surface loop for stale high-value Notion records
4. Backfill key historical docs into the archive structure
5. Reduce free-text lineage by introducing canonical keys / registries for `Project` and `Goal`

## Good defaults for the next LLM

- Prefer `rg` for discovery
- Prefer `apply_patch` for edits
- Keep the system generic, not Substack-only
- Preserve the current red-team rule: `Claude + Gemini + Codex`, `2-of-3` pass

