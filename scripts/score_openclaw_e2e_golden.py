#!/usr/bin/env python3
"""Run hand-authored golden requests through the real OpenClaw run() path."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from adapters.content import openclaw_agent


STATUS_FIXTURE = {
    "generated_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
    "runtime": {"capital_actions_enabled": False, "slack_phase": "phase-1"},
    "integrations": {
        "postgres": {"available": True},
        "notion": {"available": True, "live_checked": True, "error": None},
        "slack_bot": {"available": True, "live_checked": True, "error": None},
        "openclaw": {"available": True, "live_checked": True, "error": None},
    },
    "services": {"ollama_11434": True},
    "integrity": {"ok": True, "findings": []},
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.corpus).read_text(encoding="utf-8").splitlines() if line.strip()]
    failures = []
    with patch.object(openclaw_agent, "OPENCLAW_VERIFIED_DELIVERY_ENABLED", True), patch.object(
        openclaw_agent, "OPENCLAW_QUALITY_SHADOW_ENABLED", False
    ), patch.object(openclaw_agent, "_load_status_payload", return_value=STATUS_FIXTURE), patch.object(
        openclaw_agent, "_run_ollama_chat", side_effect=AssertionError("golden corpus must not use ungrounded model chat")
    ), patch.object(openclaw_agent, "_run_anthropic_chat", side_effect=AssertionError("golden corpus must not use ungrounded model chat")):
        def classifier(message: str):
            if message == "현재 상태 알려줘":
                return {"tool": "harness_status", "params": {}}
            return None

        with patch.object(openclaw_agent, "_run_tool_agent", return_value="unverified model response"), patch.object(
            openclaw_agent, "_classify_intent_with_haiku", side_effect=classifier
        ):
            for row in rows:
                result = str(openclaw_agent.run(row["request"], session_id=f"golden:{row['id']}:{id(rows)}"))
                missing = [value for value in row["required"] if value not in result]
                leaked = [value for value in row["forbidden"] if value in result]
                if missing or leaked:
                    failures.append({"id": row["id"], "missing": missing, "forbidden_present": leaked, "actual": result})
    report = {"scope": "openclaw_run_e2e_golden", "cases": len(rows), "failures": failures, "status": "pass" if not failures else "fail"}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "cases": len(rows), "failures": len(failures)}))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
