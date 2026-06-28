import argparse
import json
import re
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

sys.path.insert(0, ".")

from adapters.content.slack_router import send_slack_route


REPO_ROOT = Path(".")
DEFAULT_OUTPUT_DIR = Path("docs/reports/llm_outputs")

PROVIDERS = {
    "claude": {
        "route": "agent_claude_strategy",
        "build_command": lambda prompt: [_find_cli("claude"), "-p", prompt],
    },
    "codex": {
        "route": "agent_codex_review",
        "build_command": lambda prompt: [_find_cli("codex"), "exec", "--skip-git-repo-check", "-s", "read-only", prompt],
    },
    "gemini": {
        "route": "agent_gemini_research",
        "build_command": lambda prompt: [_find_cli("gemini"), "-p", prompt, "--approval-mode", "plan"],
    },
    "copilot": {
        "route": "agent_github_copilot",
        "build_command": lambda prompt: [_find_cli("copilot"), "-p", prompt, "--no-ask-user", "--silent"],
    },
}

GOVERNANCE_BOOTSTRAP_PROMPT = """\
[HARNESS GOVERNANCE BOOTSTRAP - NON-OPTIONAL]
Before analyzing or answering, treat these repo rules as already loaded and binding:
1. Read and follow CLAUDE.md for Harness operating directives, role boundaries, and completion semantics.
2. Read and follow docs/governance/LLM_GROUND_RULES.md for all LLM common non-negotiables.
3. Do not claim completion from mock/unit/local-only checks when a real user-facing or production entrypoint can be checked.
4. If a completion report is requested, include governance_bootstrap evidence for CLAUDE.md and docs/governance/LLM_GROUND_RULES.md, then validate it with scripts/agent_completion_guard.py.
5. If CEO explicitly requested Red Team, do not emit red_team_clear without two-model artifacts and a verdict.
If you cannot comply with these rules, return BLOCKED with the missing prerequisite.
"""


def _find_cli(name: str) -> str:
    for candidate in (name, f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}"):
        if Path(candidate).exists() or candidate == name:
            if candidate != name:
                return candidate
    return name


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return slug[:80] or "task"


def _timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _policy_today() -> date:
    return datetime.now(ZoneInfo("Asia/Seoul")).date()


def _gemini_red_team_enabled() -> bool:
    if _policy_today() < date(2026, 7, 1):
        return False
    return os.getenv("HARNESS_GEMINI_RED_TEAM_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _task_prompt(packet: dict[str, Any], provider: str) -> str:
    packet_json = json.dumps(packet, ensure_ascii=False, indent=2)
    return (
        f"{GOVERNANCE_BOOTSTRAP_PROMPT}\n"
        f"You are the {provider} specialist inside Harness.\n"
        "Consume the following task packet and return concise markdown with these sections only:\n"
        "1. Objective\n2. Findings\n3. Risks\n4. Recommended Next Actions\n\n"
        "If any input artifact is missing, say so explicitly.\n\n"
        f"{packet_json}\n"
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "owner": "Codex Chief of Staff",
        "task_kind": args.task_kind,
        "title": args.title,
        "objective": args.objective,
        "input_artifacts": args.input_artifact or [],
        "output_artifacts": args.output_artifact or [],
        "checks": args.check or [],
        "notes": args.note or [],
        "callback_route": args.callback_route,
    }


def dispatch_packet(packet: dict[str, Any], providers: list[str], output_dir: Path, notify_route: str | None) -> dict[str, Any]:
    task_slug = _slugify(packet["title"])
    ts = _timestamp()
    packet_path = output_dir / f"packet_{task_slug}_{ts}.json"
    _write_text(packet_path, json.dumps(packet, ensure_ascii=False, indent=2))

    is_red_team = str(packet.get("task_kind") or "").lower() == "red_team"
    if is_red_team and not _gemini_red_team_enabled():
        providers = [provider for provider in providers if provider != "gemini"]
    if is_red_team and len(set(providers)) < 2:
        raise ValueError("red_team dispatch requires at least two non-Gemini providers through 2026-06-30")

    results: list[dict[str, Any]] = []
    for provider in providers:
        spec = PROVIDERS[provider]
        prompt = _task_prompt(packet, provider)
        output_path = output_dir / f"{provider}_{task_slug}_{ts}.md"
        command = spec["build_command"](prompt)
        status = "completed"
        stdout = ""
        stderr = ""
        try:
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=240,
                check=False,
                env={
                    **os.environ,
                    "PATH": f"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{os.environ.get('PATH', '')}",
                },
            )
            stdout = completed.stdout.strip()
            stderr = completed.stderr.strip()
            if completed.returncode != 0 or not stdout:
                status = "blocked"
                stdout = stdout or stderr or f"{provider} returned code {completed.returncode}"
        except Exception as exc:
            status = "blocked"
            stdout = str(exc)

        _write_text(output_path, stdout)
        results.append(
            {
                "provider": provider,
                "status": status,
                "output_path": str(output_path),
                "route": spec["route"],
                "stderr": stderr[:500] if stderr else "",
            }
        )

        if notify_route:
            try:
                send_slack_route(
                    notify_route,
                    {"text": f"LLM task packet dispatched: {provider} -> {status} | {output_path}"},
                )
            except Exception:
                # Local/offline execution environments may not reach Slack.
                pass

        try:
            send_slack_route(
                spec["route"],
                {
                    "text": f"Harness packet `{packet['title']}` -> {status}\npacket={packet_path}\noutput={output_path}",
                },
            )
        except Exception:
            # Local/offline execution environments may not reach Slack.
            pass

    return {"packet_path": str(packet_path), "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch a Harness task packet to external LLM CLIs.")
    parser.add_argument("task_kind")
    parser.add_argument("title")
    parser.add_argument("--objective", required=True)
    parser.add_argument("--provider", action="append", choices=sorted(PROVIDERS), dest="providers")
    parser.add_argument("--input-artifact", action="append")
    parser.add_argument("--output-artifact", action="append")
    parser.add_argument("--check", action="append")
    parser.add_argument("--note", action="append")
    parser.add_argument("--callback-route", default="agent_openclaw_routing")
    parser.add_argument("--notify-route", default="agent_openclaw_routing")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    default_providers = ["claude", "gemini", "copilot"]
    providers = args.providers or default_providers
    packet = build_packet(args)
    try:
        result = dispatch_packet(packet, providers, args.output_dir, args.notify_route)
    except ValueError as exc:
        print(json.dumps({"status": "blocked", "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
