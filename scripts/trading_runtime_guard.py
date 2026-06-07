#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=True)

from ib_insync import IB  # noqa: E402
from scripts.alpaca_paper_trading import get_account_summary  # noqa: E402

REPORT_PATH = ROOT / "docs" / "reports" / "trading_runtime_guard.json"

ALPACA_SCRIPT = ROOT / "scripts" / "run_trading_cycle.py"
UNIVERSE_SCRIPT = ROOT / "scripts" / "build_trading_universe.py"
RESET_WATCH_SCRIPT = ROOT / "scripts" / "check_paper_books_flat.py"
IBKR_TRADER_SCRIPT = ROOT / "scripts" / "ibkr_tws_paper_trader.py"
POST_OPEN_VERIFICATION_SCRIPT = ROOT / "scripts" / "run_post_open_verification.py"

ALPACA_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.harness.turtle-auto-trader.plist"
IBKR_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.harness.ibkr-auto-trader.plist"
RESET_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.harness.paper-reset-watch.plist"
POST_OPEN_PLIST = Path.home() / "Library" / "LaunchAgents" / "com.harness.post-open-verification.plist"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def launchctl_row(label: str) -> dict:
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=10).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2] == label:
                return {"pid": parts[0], "exit": parts[1], "label": parts[2]}
    except Exception as e:
        return {"error": str(e)}
    return {"pid": "-", "exit": "-", "label": label}


def check_file(path: Path) -> dict:
    return {"path": str(path), "exists": path.exists()}


def check_alpaca() -> dict:
    summary = get_account_summary()
    return {
        "ok": bool(summary.get("ok")),
        "status": summary.get("status"),
        "error": summary.get("error"),
    }


def check_ibkr() -> dict:
    port = 4002 if os.getenv("IBKR_TRADING_MODE", "paper").strip().lower() == "paper" else 4001
    ib = IB()
    try:
        ib.connect("127.0.0.1", port, clientId=289, timeout=10)
        return {"ok": True, "port": port, "accounts": ib.managedAccounts()}
    except Exception as e:
        return {"ok": False, "port": port, "error": str(e)}
    finally:
        if ib.isConnected():
            ib.disconnect()


def derive_issues(payload: dict) -> list[str]:
    issues: list[str] = []
    for key in (
        "alpaca_script",
        "universe_script",
        "reset_watch_script",
        "ibkr_trader_script",
        "post_open_verification_script",
        "alpaca_plist",
        "ibkr_plist",
        "reset_plist",
        "post_open_plist",
    ):
        if not payload[key]["exists"]:
            issues.append(f"missing:{key}")
    if not payload["alpaca_auth"]["ok"]:
        issues.append("alpaca_auth_failed")
    if not payload["ibkr_gateway"]["ok"]:
        issues.append("ibkr_gateway_failed")
    for label_key in ("alpaca_launchd", "ibkr_launchd", "reset_watch_launchd"):
        row = payload[label_key]
        if row.get("pid") == "-" and row.get("exit") not in ("0", "-"):
            issues.append(f"launchd_failed:{row.get('label')}")
    return issues


def main() -> int:
    payload = {
        "checked_at": now_iso(),
        "alpaca_script": check_file(ALPACA_SCRIPT),
        "universe_script": check_file(UNIVERSE_SCRIPT),
        "reset_watch_script": check_file(RESET_WATCH_SCRIPT),
        "ibkr_trader_script": check_file(IBKR_TRADER_SCRIPT),
        "post_open_verification_script": check_file(POST_OPEN_VERIFICATION_SCRIPT),
        "alpaca_plist": check_file(ALPACA_PLIST),
        "ibkr_plist": check_file(IBKR_PLIST),
        "reset_plist": check_file(RESET_PLIST),
        "post_open_plist": check_file(POST_OPEN_PLIST),
        "alpaca_launchd": launchctl_row("com.harness.turtle-auto-trader"),
        "ibkr_launchd": launchctl_row("com.harness.ibkr-auto-trader"),
        "reset_watch_launchd": launchctl_row("com.harness.paper-reset-watch"),
        "post_open_launchd": launchctl_row("com.harness.post-open-verification"),
        "alpaca_auth": check_alpaca(),
        "ibkr_gateway": check_ibkr(),
    }
    payload["issues"] = derive_issues(payload)
    payload["ok"] = not payload["issues"]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
