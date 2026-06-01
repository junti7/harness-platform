"""LLM fallback state tracking — manages temporary provider switches.

When a persona's primary LLM runs out of credits, we:
  1. Record the fallback state with timestamp.
  2. Use the fallback provider for that persona.
  3. Periodically check if the primary provider is back online.
  4. Auto-revert to primary when available.

Fallback states are stored in runtime/persona_llm_fallback.json:
  {
    "c3po": {
      "primary_provider": "gemini",
      "current_provider": "claude",
      "switched_at": "2026-05-31T19:00:00Z",
      "reason": "usage_limit_exceeded",
      "last_retry": "2026-05-31T19:10:00Z"
    }
  }
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adapters.content.slack_router import send_slack_route

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FALLBACK_STATE_PATH = PROJECT_ROOT / "runtime/persona_llm_fallback.json"
FALLBACK_EVENTS_PATH = PROJECT_ROOT / "runtime/persona_llm_fallback_events.jsonl"
NOTIFY_COOLDOWN_SECONDS = int(os.getenv("PERSONA_FALLBACK_NOTIFY_COOLDOWN_SEC", "1800"))


def _load_fallback_state() -> dict[str, dict[str, Any]]:
    """Load current fallback state from file."""
    if not FALLBACK_STATE_PATH.exists():
        return {}
    try:
        text = FALLBACK_STATE_PATH.read_text(encoding="utf-8")
        return json.loads(text) if text.strip() else {}
    except Exception:
        return {}


def _save_fallback_state(state: dict[str, dict[str, Any]]) -> None:
    """Save fallback state to file."""
    FALLBACK_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FALLBACK_STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_fallback_event(event: dict[str, Any]) -> None:
    FALLBACK_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FALLBACK_EVENTS_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


def _persona_label(handle: str) -> str:
    try:
        from agents.registry import get_persona

        persona = get_persona(handle)
        return persona.display
    except Exception:
        return handle


def _post_fallback_incident(handle: str, primary: str, current: str, reason: str, *, recovered: bool = False) -> None:
    label = _persona_label(handle)
    if recovered:
        text = (
            f"*Persona Fallback Recovery*\n"
            f"- persona: `{label}`\n"
            f"- active provider: `{current}`\n"
            f"- status: recovered to primary"
        )
    else:
        text = (
            f"*Persona Fallback Activated*\n"
            f"- persona: `{label}`\n"
            f"- primary: `{primary}`\n"
            f"- active provider: `{current}`\n"
            f"- reason: `{reason}`"
        )
    try:
        send_slack_route("ops_incidents", {"text": text})
    except Exception:
        pass


def _record_fallback_event(handle: str, primary: str, current: str, reason: str, *, event_type: str) -> None:
    _append_fallback_event(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "persona_handle": handle,
            "persona_display": _persona_label(handle),
            "primary_provider": primary,
            "active_provider": current,
            "reason": reason,
        }
    )


def _is_provider_available(provider: str, timeout: int = 5) -> bool:
    """Quick smoke test using a minimal real call, not just --version."""
    try:
        if provider == "claude":
            cli = "/opt/homebrew/bin/claude"
            completed = subprocess.run(
                [cli, "-p", "-"],
                input="reply with ok",
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            stdout = (completed.stdout or "").lower()
            stderr = (completed.stderr or "").lower()
            if completed.returncode != 0:
                return False
            if (
                "credit balance is too low" in stdout
                or "credit balance is too low" in stderr
                or "usage limit" in stdout
                or "usage limit" in stderr
                or "quota" in stdout
                or "quota" in stderr
            ):
                return False
            return True
        elif provider == "gemini":
            cli = "/opt/homebrew/bin/gemini"
            completed = subprocess.run(
                [cli, "--skip-trust", "-p", "reply with ok", "-o", "text"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            stdout = (completed.stdout or "").lower()
            stderr = (completed.stderr or "").lower()
            if completed.returncode != 0:
                return False
            if "usage limit" in stdout or "usage limit" in stderr or "quota" in stdout or "quota" in stderr:
                return False
            return True
        elif provider == "codex":
            # For codex, --version returns 0 even if token is expired or usage limit is hit.
            # We run a quick exec check to verify actual availability.
            try:
                cli = "/opt/homebrew/bin/codex"
                completed = subprocess.run(
                    [cli, "exec", "--sandbox", "read-only", "-"],
                    input="hello",
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                if completed.returncode != 0:
                    return False
                stdout = (completed.stdout or "").lower()
                stderr = (completed.stderr or "").lower()
                if "usage limit" in stdout or "usage limit" in stderr or "unauthorized" in stdout or "unauthorized" in stderr:
                    return False
                return True
            except Exception:
                return False
        elif provider == "copilot":
            cmd = ["/opt/homebrew/bin/copilot", "--version"]
        else:
            return True  # Unknown provider, assume available
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode == 0
    except Exception:
        return False


def record_fallback(persona_handle: str, primary_provider: str, fallback_provider: str, reason: str) -> None:
    """Record that persona switched to fallback provider."""
    state = _load_fallback_state()
    now = datetime.now(timezone.utc)
    previous = state.get(persona_handle) or {}
    should_notify = True
    if previous.get("current_provider") == fallback_provider and previous.get("reason") == reason:
        last_notified = str(previous.get("last_notified_at") or "")
        if last_notified:
            try:
                notified_at = datetime.fromisoformat(last_notified)
                if (now - notified_at).total_seconds() < NOTIFY_COOLDOWN_SECONDS:
                    should_notify = False
            except Exception:
                pass
    state[persona_handle] = {
        "primary_provider": primary_provider,
        "current_provider": fallback_provider,
        "switched_at": now.isoformat(),
        "reason": reason,
        "last_retry": now.isoformat(),
        "last_notified_at": now.isoformat() if should_notify else previous.get("last_notified_at"),
    }
    _save_fallback_state(state)
    _record_fallback_event(persona_handle, primary_provider, fallback_provider, reason, event_type="fallback_activated")
    if should_notify:
        _post_fallback_incident(persona_handle, primary_provider, fallback_provider, reason)


def get_current_provider(persona_handle: str, registered_primary: str, registered_fallback: str | None) -> str:
    """Get the currently active provider for a persona.
    
    Returns:
      - If in fallback state and fallback is available: fallback provider
      - If in fallback state but primary recovered: primary provider (and clear state)
      - Otherwise: registered primary provider
    """
    if not registered_fallback:
        return registered_primary
    
    state = _load_fallback_state()
    fallback_entry = state.get(persona_handle)
    
    if not fallback_entry:
        return registered_primary
    
    # Currently in fallback mode. Check if primary is back.
    current_time = datetime.now(timezone.utc)
    last_retry_str = fallback_entry.get("last_retry")
    
    # Retry every 5 minutes
    if last_retry_str:
        last_retry = datetime.fromisoformat(last_retry_str)
        if (current_time - last_retry).total_seconds() < 300:
            # Still in retry cooldown, stay on fallback
            return fallback_entry["current_provider"]
    
    # Time to check if primary is available
    if _is_provider_available(registered_primary):
        # Primary recovered! Clear fallback state and switch back.
        previous = dict(fallback_entry)
        del state[persona_handle]
        _save_fallback_state(state)
        _record_fallback_event(
            persona_handle,
            str(previous.get("primary_provider") or registered_primary),
            registered_primary,
            str(previous.get("reason") or "recovered"),
            event_type="fallback_recovered",
        )
        _post_fallback_incident(
            persona_handle,
            str(previous.get("primary_provider") or registered_primary),
            registered_primary,
            str(previous.get("reason") or "recovered"),
            recovered=True,
        )
        return registered_primary
    else:
        # Primary still unavailable. Update last_retry and stay on fallback.
        fallback_entry["last_retry"] = current_time.isoformat()
        _save_fallback_state(state)
        return fallback_entry["current_provider"]


def clear_fallback(persona_handle: str) -> None:
    """Manually clear fallback state for a persona."""
    state = _load_fallback_state()
    if persona_handle in state:
        previous = dict(state[persona_handle])
        del state[persona_handle]
        _save_fallback_state(state)
        _record_fallback_event(
            persona_handle,
            str(previous.get("primary_provider") or ""),
            str(previous.get("primary_provider") or ""),
            str(previous.get("reason") or "manual_clear"),
            event_type="fallback_cleared",
        )
        _post_fallback_incident(
            persona_handle,
            str(previous.get("primary_provider") or ""),
            str(previous.get("primary_provider") or ""),
            str(previous.get("reason") or "manual_clear"),
            recovered=True,
        )


def get_fallback_info(persona_handle: str) -> dict[str, Any] | None:
    """Get fallback state for a persona (for logging/debugging)."""
    state = _load_fallback_state()
    return state.get(persona_handle)


def load_recent_fallback_events(limit: int = 10) -> list[dict[str, Any]]:
    if not FALLBACK_EVENTS_PATH.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with FALLBACK_EVENTS_PATH.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return rows[-limit:][::-1]


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python llm_fallback_manager.py <command> [args]")
        print("Commands:")
        print("  status [persona]           - show fallback status")
        print("  record <p> <prim> <fb> <r> - record fallback (prim=primary, fb=fallback, r=reason)")
        print("  clear <persona>            - clear fallback state")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        persona = sys.argv[2] if len(sys.argv) > 2 else None
        all_state = _load_fallback_state()
        if persona:
            info = all_state.get(persona)
            print(json.dumps(info or {}, indent=2))
        else:
            print(json.dumps(all_state, indent=2))
    elif cmd == "record":
        if len(sys.argv) < 6:
            print("Usage: python llm_fallback_manager.py record <persona> <primary> <fallback> <reason>")
            sys.exit(1)
        record_fallback(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        print(f"✓ Recorded fallback for {sys.argv[2]}: {sys.argv[3]} → {sys.argv[4]} ({sys.argv[5]})")
    elif cmd == "clear":
        if len(sys.argv) < 3:
            print("Usage: python llm_fallback_manager.py clear <persona>")
            sys.exit(1)
        clear_fallback(sys.argv[2])
        print(f"✓ Cleared fallback for {sys.argv[2]}")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
