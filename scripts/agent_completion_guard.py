#!/usr/bin/env python3
"""Validate that an agent closeout report has real verification evidence.

This guard is intentionally small and strict. It does not prove a task is
correct; it blocks the two failure modes that caused repeated regressions:
mock-only verification and claiming red-team/deploy completion without artifacts.

Evidence schema:

{
  "task": "short task name",
  "status": "complete|blocked|residual_risk",
  "governance_bootstrap": [
    {
      "path": "CLAUDE.md",
      "read_at": "2026-06-28T14:30:00+09:00",
      "summary": "Must/Never, real verification, deployment SoT checked before analysis"
    },
    {
      "path": "docs/governance/LLM_GROUND_RULES.md",
      "read_at": "2026-06-28T14:30:00+09:00",
      "summary": "Completion requires real user-facing/runtime verification evidence"
    }
  ],
  "verification": [
    {
      "name": "macmini production answer check",
      "target": "macmini api",
      "command": "curl ...",
      "result": "observed expected behavior"
    }
  ],
  "deploy": {
    "method": "scripts/deploy_to_macmini.sh path...",
    "result": "deployed and verified"
  },
  "red_team": {
    "models": ["Claude", "Copilot"],
    "artifacts": [{"artifact": "claude.md"}, {"artifact": "gemini.md"}],
    "verdict": "red_team_clear|red_team_block|red_team_residual_risk"
  }
}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = {"task", "status", "governance_bootstrap", "verification"}
REQUIRED_BOOTSTRAP_FILES = {"CLAUDE.md", "docs/governance/LLM_GROUND_RULES.md"}
REAL_ENTRYPOINT_MARKERS = {
    "macmini",
    "production",
    "prod",
    "browser",
    "playwright",
    "api",
    "curl",
    "db",
    "database",
    "launchd",
    "dist",
    "service",
    "url",
    "mobile",
    "pre-push",
    "git hook",
    "llm dispatch",
    "persona dispatch",
}


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"invalid JSON evidence: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("evidence root must be a JSON object")
    return data


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _artifacts_exist(items: list[dict[str, Any]], base_dir: Path) -> list[str]:
    missing: list[str] = []
    for item in items:
        artifact = str(item.get("artifact") or "").strip()
        if not artifact:
            continue
        path = Path(artifact)
        if not path.is_absolute():
            path = base_dir / path
        if not path.exists():
            missing.append(artifact)
    return missing


def validate(data: dict[str, Any], *, base_dir: Path, require_deploy: bool, require_red_team: bool) -> list[str]:
    errors: list[str] = []
    missing_top = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing_top:
        errors.append(f"missing top-level fields: {', '.join(missing_top)}")

    status = str(data.get("status") or "").strip()
    if status not in {"complete", "blocked", "residual_risk"}:
        errors.append("status must be one of: complete, blocked, residual_risk")

    bootstrap = data.get("governance_bootstrap")
    if not isinstance(bootstrap, list) or not bootstrap:
        errors.append("governance_bootstrap must list the ground-rule files read before analysis")
        bootstrap = []
    read_files: set[str] = set()
    for idx, item in enumerate(bootstrap, start=1):
        if not isinstance(item, dict):
            errors.append(f"governance_bootstrap[{idx}] must be an object")
            continue
        path = str(item.get("path") or "").strip()
        read_at = str(item.get("read_at") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if path:
            read_files.add(path)
        if path not in REQUIRED_BOOTSTRAP_FILES:
            errors.append(f"governance_bootstrap[{idx}] unexpected path: {path or '<missing>'}")
        if not read_at:
            errors.append(f"governance_bootstrap[{idx}] missing read_at")
        if len(summary) < 20:
            errors.append(f"governance_bootstrap[{idx}] summary is too short")
    missing_bootstrap = sorted(REQUIRED_BOOTSTRAP_FILES - read_files)
    if missing_bootstrap:
        errors.append(f"missing required governance bootstrap file(s): {', '.join(missing_bootstrap)}")

    verification = data.get("verification")
    if not isinstance(verification, list) or not verification:
        errors.append("verification must be a non-empty list")
        verification = []

    real_entrypoint_count = 0
    mock_only_count = 0
    for idx, item in enumerate(verification, start=1):
        if not isinstance(item, dict):
            errors.append(f"verification[{idx}] must be an object")
            continue
        name = str(item.get("name") or "").strip()
        command = str(item.get("command") or "").strip()
        result = str(item.get("result") or "").strip()
        target = str(item.get("target") or "").strip().lower()
        if not name:
            errors.append(f"verification[{idx}] missing name")
        if not result:
            errors.append(f"verification[{idx}] missing result")
        blob = " ".join([name.lower(), command.lower(), result.lower(), target])
        if item.get("mock") is True or "mock" in blob or "patch.object" in blob:
            mock_only_count += 1
        if any(marker in blob for marker in REAL_ENTRYPOINT_MARKERS):
            real_entrypoint_count += 1

    if real_entrypoint_count == 0:
        errors.append("at least one verification must hit a real user-facing/runtime entrypoint")
    if mock_only_count and mock_only_count == len(verification):
        errors.append("mock-only verification cannot support a complete closeout")

    deployed = data.get("deploy")
    if require_deploy or deployed:
        if not isinstance(deployed, dict):
            errors.append("deploy must be an object when deploy is required")
        else:
            method = str(deployed.get("method") or "")
            result = str(deployed.get("result") or "")
            if "scripts/deploy_to_macmini.sh" not in method:
                errors.append("deploy.method must use scripts/deploy_to_macmini.sh")
            if not result:
                errors.append("deploy.result is required")

    red_team = data.get("red_team")
    if require_red_team or red_team:
        if not isinstance(red_team, dict):
            errors.append("red_team must be an object when red-team is required")
        else:
            models = red_team.get("models")
            if not isinstance(models, list):
                models = []
            normalized = {str(model).strip().lower() for model in models}
            independent_second = {"codex", "copilot", "gemini", "gpt reasoning", "gpt-reasoning"}
            if "claude" not in normalized or not (normalized & independent_second):
                errors.append("red_team.models must include Claude plus Codex, Copilot, Gemini, or GPT reasoning")
            artifacts = red_team.get("artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                errors.append("red_team.artifacts must be a non-empty list")
                artifacts = []
            missing = _artifacts_exist([item for item in artifacts if isinstance(item, dict)], base_dir)
            if missing:
                errors.append(f"red_team artifact(s) missing: {', '.join(missing)}")
            verdict = str(red_team.get("verdict") or "").strip()
            if verdict not in {"red_team_clear", "red_team_block", "red_team_residual_risk"}:
                errors.append("red_team.verdict must be red_team_clear, red_team_block, or red_team_residual_risk")

    if status == "complete" and errors:
        errors.append("status=complete is invalid while guard errors exist")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_json", type=Path)
    parser.add_argument("--require-deploy", action="store_true")
    parser.add_argument("--require-red-team", action="store_true")
    args = parser.parse_args(argv)

    data = _load(args.evidence_json)
    errors = validate(
        data,
        base_dir=args.evidence_json.resolve().parent,
        require_deploy=args.require_deploy,
        require_red_team=args.require_red_team,
    )
    if errors:
        print("completion_guard: BLOCK")
        for error in errors:
            print(f"- {error}")
        return 1
    print("completion_guard: CLEAR")
    print(_stringify({"task": data.get("task"), "status": data.get("status")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
