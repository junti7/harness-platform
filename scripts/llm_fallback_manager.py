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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FALLBACK_STATE_PATH = PROJECT_ROOT / "runtime/persona_llm_fallback.json"


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


def _is_provider_available(provider: str, timeout: int = 5) -> bool:
    """Quick smoke test: can provider CLI be called?"""
    try:
        if provider == "claude":
            cmd = ["/opt/homebrew/bin/claude", "--version"]
        elif provider == "gemini":
            cmd = ["/opt/homebrew/bin/gemini", "--version"]
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
    state[persona_handle] = {
        "primary_provider": primary_provider,
        "current_provider": fallback_provider,
        "switched_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "last_retry": datetime.now(timezone.utc).isoformat(),
    }
    _save_fallback_state(state)


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
        del state[persona_handle]
        _save_fallback_state(state)
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
        del state[persona_handle]
        _save_fallback_state(state)


def get_fallback_info(persona_handle: str) -> dict[str, Any] | None:
    """Get fallback state for a persona (for logging/debugging)."""
    state = _load_fallback_state()
    return state.get(persona_handle)


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
