#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "harness-os" / "backend" / "main.py"


def _load_backend() -> Any:
    module_name = "harness_backend_main_for_edu_downvote_reprocessor"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, BACKEND_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load backend module: {BACKEND_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_once(*, limit: int = 100) -> dict[str, Any]:
    backend = _load_backend()
    if hasattr(backend, "_ensure_edu_case_schema"):
        backend._ensure_edu_case_schema()
    result = backend._edu_vp_reprocess_pending_safety_coach_downvotes(limit=limit)
    if not isinstance(result, dict):
        raise RuntimeError("downvote reprocessor returned non-dict result")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Reprocess pending EDU safety-coach downvote auto-reinforcement reviews.")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    try:
        result = run_once(limit=args.limit)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
