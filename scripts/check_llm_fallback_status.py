#!/usr/bin/env python3
"""Check persona LLM fallback status and auto-recover when primary is available.

This script runs periodically (e.g., every 5-10 minutes via cron) to:
  1. Check which personas are in fallback mode.
  2. Test if their primary LLM is back online.
  3. Clear fallback state if primary recovered.
  4. Log the status.

Usage:
  python scripts/check_llm_fallback_status.py
  
For cron:
  */5 * * * * cd /path/to/harness-platform && source .venv/bin/activate && python scripts/check_llm_fallback_status.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.llm_fallback_manager import _load_fallback_state, _is_provider_available, clear_fallback, _save_fallback_state

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FALLBACK_STATE_PATH = PROJECT_ROOT / "runtime/persona_llm_fallback.json"
STATUS_LOG_PATH = PROJECT_ROOT / "logs/llm_fallback_check.log"


def check_and_recover():
    """Check fallback state and attempt recovery."""
    state = _load_fallback_state()
    
    if not state:
        return {"status": "ok", "message": "No personas in fallback mode", "checked_at": datetime.now().isoformat()}
    
    results = {}
    recovered = []
    still_down = []
    
    for persona_handle, fallback_info in state.items():
        primary = fallback_info.get("primary_provider", "unknown")
        current = fallback_info.get("current_provider", "unknown")
        switched_at = fallback_info.get("switched_at", "unknown")
        
        # Test primary provider
        is_available = _is_provider_available(primary, timeout=5)
        
        if is_available:
            # Primary recovered!
            clear_fallback(persona_handle)
            recovered.append(f"{persona_handle} ({primary})")
        else:
            # Primary still down
            still_down.append(f"{persona_handle} (→ {current})")
        
        results[persona_handle] = {
            "primary": primary,
            "current": current,
            "switched_at": switched_at,
            "primary_available": is_available,
            "recovered": is_available,
        }
    
    # Log result
    summary = {
        "checked_at": datetime.now().isoformat(),
        "total_fallback": len(state),
        "recovered": len(recovered),
        "still_down": len(still_down),
        "details": results,
    }
    
    # Append to log
    STATUS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(summary, ensure_ascii=False) + "\n")
    
    # Print summary
    if recovered:
        print(f"✓ Recovered {len(recovered)} persona(s): {', '.join(recovered)}")
    if still_down:
        print(f"⚠️  Still in fallback {len(still_down)} persona(s): {', '.join(still_down)}")
    if not recovered and not still_down:
        print("✓ All clear — no personas in fallback mode")
    
    return summary


if __name__ == "__main__":
    try:
        result = check_and_recover()
        sys.exit(0)
    except Exception as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        sys.exit(1)
