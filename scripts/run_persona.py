"""Single-persona runner — the smallest unit of the agentic orchestration loop.

Given a persona handle (from agents/registry.py) and a task, this:
  1. loads the persona's SYSTEM_PROMPT.md,
  2. calls the persona's primary LLM CLI (claude/gemini/codex/copilot),
  3. posts the persona's opinion to its Slack home channel (구어체, Charter §4.3),
  4. appends a factual run-record to the persona's MEMORY.md (Charter §8).

It works for ANY active persona — adding teams later needs no change here, only a
registry entry + active flag + channel. The orchestrator (adapters/content/
orchestrator.py) imports call_persona / post_opinion / call_llm from this module.

Usage:
    python scripts/run_persona.py friday --task "이번 주 무료 구독자 정체 원인 봐줘"
    python scripts/run_persona.py friday --task "..." --dry-run    # no LLM, no post
    python scripts/run_persona.py kitt   --task "..." --no-post     # call LLM, skip Slack
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adapters.content.slack_format import to_slack_mrkdwn  # noqa: E402
from agents.registry import Persona, get_persona  # noqa: E402

load_dotenv(override=True)

PROVIDER_TIMEOUT = 240


# ── LLM invocation ──────────────────────────────────────────────────────────

def _find_cli(name: str) -> str:
    for candidate in (f"/opt/homebrew/bin/{name}", f"/usr/local/bin/{name}", name):
        if candidate == name or Path(candidate).exists():
            return candidate
    return name


def _build_command(provider: str, prompt: str) -> list[str]:
    cli = _find_cli(provider)
    if provider == "claude":
        return [cli, "-p", prompt]
    if provider == "gemini":
        return [cli, "-p", prompt, "--approval-mode", "plan", "-o", "text"]
    if provider == "codex":
        return [cli, "exec", "--sandbox", "read-only", prompt]
    if provider == "copilot":
        return [cli, "-p", prompt, "--no-ask-user", "--silent"]
    raise ValueError(f"Unknown provider: {provider}")


def call_llm(provider: str, prompt: str) -> tuple[str, bool]:
    """Run a provider CLI with a fully-formed prompt. Returns (text, ok)."""
    command = _build_command(provider, prompt)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=PROVIDER_TIMEOUT,
            check=False,
            env={
                **os.environ,
                "PATH": f"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{os.environ.get('PATH', '')}",
            },
        )
    except Exception as exc:  # noqa: BLE001
        return f"({provider} 호출 실패: {exc})", False

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0 or not stdout:
        return f"({provider} 응답 없음: {stdout or stderr or completed.returncode})", False
    return stdout, True


def _build_prompt(persona: Persona, task: str, correlation_id: str, extra_context: str = "") -> str:
    system = ""
    if persona.system_prompt_path.exists():
        system = persona.system_prompt_path.read_text(encoding="utf-8").strip()
    context_block = f"\n[참고 — 다른 팀 발언]\n{extra_context}\n" if extra_context else ""
    return (
        f"{system}\n\n"
        "─────────────────────────────────────\n"
        f"[correlation_id: {correlation_id}]\n"
        f"이건 #{persona.team_short} / #회의실 에 올라갈 발언입니다. Charter §4.3대로 **공손한 존댓말 구어체**로, "
        "회사 동료처럼 자연스럽게 말씀해 주세요. **반말 금지**(회사에서는 반말을 쓰지 않습니다), 보고서 문체도 금지. "
        "다른 팀을 언급할 때는 'Friday님', 'KITT님'처럼 반드시 '님'을 붙입니다. "
        "근거(지표/법령 등)는 대화 속에 녹이고, 추정이면 confidence를 밝혀 주세요."
        f"{context_block}\n"
        f"[TASK]\n{task}\n"
    )


def call_persona(
    persona: Persona,
    task: str,
    correlation_id: str,
    extra_context: str = "",
) -> tuple[str, bool]:
    """Build the persona prompt and call its primary LLM. Returns (text, ok)."""
    prompt = _build_prompt(persona, task, correlation_id, extra_context)
    return call_llm(persona.provider, prompt)


# ── Slack + memory ────────────────────────────────────────────────────────────

def post_opinion(persona: Persona, text: str, channel_id: str | None = None) -> bool:
    """Post a persona's message to its home channel. Returns True if posted."""
    channel_id = channel_id or (os.getenv(persona.channel_env, "") if persona.channel_env else "")
    if not channel_id:
        return False
    token = os.getenv("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is not configured")
    body = f"*{persona.display}*:\n{to_slack_mrkdwn(text)}"
    resp = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"channel": channel_id, "text": body[:3900]},
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Slack postMessage failed: {data.get('error')}")
    return True


def append_diary(persona: Persona, correlation_id: str, task: str, posted: bool, ok: bool) -> None:
    """Append a factual run-record (not a fabricated reflection). Charter §8."""
    if not persona.memory_path.exists():
        return
    today = datetime.now().strftime("%Y-%m-%d")
    task_line = " ".join(task.split())[:80]
    status = "posted" if posted else ("llm_ok_no_post" if ok else "failed")
    entry = (
        f"\n## {today} {correlation_id} {task_line}\n"
        f"- what_i_did: run_persona 실행 → 채널 발언 ({status})\n"
        f"- what_worked: (자기평가 미작성)\n"
        f"- what_failed: (자기평가 미작성)\n"
        f"- lesson: (자기평가 미작성 — auto run-record)\n"
        f"- confidence: {'medium' if ok else 'low'}\n"
    )
    with persona.memory_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single persona on a task.")
    parser.add_argument("handle", help="persona handle (e.g. friday, kitt, jarvis)")
    parser.add_argument("--task", required=True, help="the question/task for the persona")
    parser.add_argument("--correlation-id", default=None)
    parser.add_argument("--dry-run", action="store_true", help="validate wiring; no LLM call, no post")
    parser.add_argument("--no-post", action="store_true", help="call LLM but skip Slack post")
    args = parser.parse_args()

    persona = get_persona(args.handle)
    correlation_id = args.correlation_id or f"persona-{uuid.uuid4().hex[:8]}"

    if persona.frozen:
        print(f"BLOCKED: '{persona.handle}'는 frozen persona (Charter §2.3, 첫 paid subscriber까지 동결).")
        return 2

    channel_id = os.getenv(persona.channel_env, "") if persona.channel_env else ""

    if args.dry_run:
        print(f"[dry-run] persona={persona.display}")
        print(f"[dry-run] provider={persona.provider} escalation={persona.escalation}")
        print(f"[dry-run] active={persona.active} channel_env={persona.channel_env} -> {channel_id or '(unset)'}")
        print(f"[dry-run] system_prompt exists: {persona.system_prompt_path.exists()}")
        print(f"[dry-run] correlation_id={correlation_id}")
        print("[dry-run] OK — 실제 호출/포스트 없음.")
        return 0

    if not persona.active:
        print(f"BLOCKED: '{persona.handle}'는 아직 inactive. registry에서 active=True + 채널 생성 후 실행.")
        return 2

    output, ok = call_persona(persona, args.task, correlation_id)
    print(f"[{persona.display}] provider={persona.provider} ok={ok} cid={correlation_id}")

    posted = False
    if ok and not args.no_post:
        posted = post_opinion(persona, output)
        if posted:
            print(f"[{persona.display}] posted to {persona.channel_env} ({channel_id})")
        else:
            print(f"WARN: {persona.channel_env} 미설정 — 포스트 생략.")

    append_diary(persona, correlation_id, args.task, posted, ok)
    print(f"--- {persona.display} output ---\n{output[:1500]}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
