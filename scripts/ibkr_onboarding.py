from __future__ import annotations

import argparse
import json
import socket
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = PROJECT_ROOT / "docs/trading/ibkr_onboarding_status.json"
_MONITOR_CACHE_PATH = PROJECT_ROOT / "docs/reports/ibkr_monitor_cache.json"
_TWS_PORT = 4002


def _check_tws() -> tuple[bool, bool, bool]:
    """(tws_reachable, tws_authenticated, tws_account_visible) via port 4002 + monitor cache."""
    # monitor cache 먼저 읽기 (ibkr_turtle_monitor가 기록한 최신 상태)
    cache: dict[str, Any] = {}
    if _MONITOR_CACHE_PATH.exists():
        try:
            cache = json.loads(_MONITOR_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 직접 소켓 체크, 실패하면 캐시의 gateway_connected 를 fallback으로 사용
    reachable = False
    try:
        with socket.create_connection(("127.0.0.1", _TWS_PORT), timeout=1.0):
            reachable = True
    except OSError:
        reachable = bool(cache.get("gateway_connected"))

    if not reachable:
        return False, False, False

    account_visible = bool((cache.get("account") or {}).get("account_id"))
    return True, account_visible, account_visible

MANUAL_STEP_DEFS = [
    ("account_opened", "IBKR Pro account opened", "Open an IBKR Pro individual account."),
    ("kyc_complete", "KYC / identity verification complete", "Identity verification must be fully accepted."),
    ("two_factor_enabled", "2FA enabled", "Enable a Client Portal API supported 2FA method."),
    ("funded", "Account funded", "Fund the account before expecting live market data."),
    (
        "permissions_set",
        "Trading permissions set for target markets",
        "Grant stock and ETF permissions for Korea, US, Japan, and Europe as needed.",
    ),
    (
        "market_data_enabled",
        "Required market-data subscriptions enabled",
        "Subscribe only to the exchanges required by the operating watchlist.",
    ),
]

AUTO_STEP_DEFS = [
    (
        "gateway_installed",
        "Client Portal Gateway installed",
        "Marked complete when localhost gateway is reachable.",
    ),
    (
        "gateway_authenticated",
        "Gateway login + 2FA session active",
        "Derived from IBKR auth status in preflight.",
    ),
    (
        "harness_verified",
        "Harness sees at least one visible account",
        "Derived from /portfolio/accounts visibility.",
    ),
]


def _default_payload() -> dict[str, Any]:
    return {
        "updated_at": datetime.now().date().isoformat(),
        "owner_note": (
            "Manual items should be updated after each IBKR onboarding milestone. "
            "Auto items are derived from gateway connectivity and account visibility."
        ),
        "steps": [
            {"id": step_id, "completed": False, "source": "manual", "note": note}
            for step_id, _label, note in MANUAL_STEP_DEFS
        ],
    }


def load_status_file() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return _default_payload()
    return json.loads(STATUS_PATH.read_text(encoding="utf-8"))


def save_status_file(payload: dict[str, Any]) -> None:
    payload["updated_at"] = datetime.now().date().isoformat()
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compute_status(preflight: dict[str, Any], accounts_payload: dict[str, Any]) -> dict[str, Any]:
    payload = load_status_file()
    steps_payload = payload.get("steps") if isinstance(payload, dict) else None
    step_map = {step.get("id"): step for step in steps_payload or [] if isinstance(step, dict)}

    def manual_step(step_id: str, label: str, note: str) -> dict[str, Any]:
        raw = step_map.get(step_id, {})
        return {
            "id": step_id,
            "label": label,
            "completed": bool(raw.get("completed", False)),
            "source": raw.get("source") or "manual",
            "note": raw.get("note") or note,
        }

    def auto_step(step_id: str, label: str, note: str, completed: bool) -> dict[str, Any]:
        raw = step_map.get(step_id, {})
        return {
            "id": step_id,
            "label": label,
            "completed": bool(completed),
            "source": raw.get("source") or "auto",
            "note": raw.get("note") or note,
        }

    auth = preflight.get("auth") or {}
    cp_ok = bool(preflight.get("ok"))
    cp_authenticated = auth.get("authenticated") is True
    cp_account_visible = int(accounts_payload.get("count") or 0) > 0

    tws_reachable, tws_authenticated, tws_account_visible = _check_tws()

    gateway_ok = cp_ok or tws_reachable
    authenticated = cp_authenticated or tws_authenticated
    account_visible = cp_account_visible or tws_account_visible

    steps = [manual_step(step_id, label, note) for step_id, label, note in MANUAL_STEP_DEFS]
    steps.extend(
        [
            auto_step("gateway_installed", AUTO_STEP_DEFS[0][1], AUTO_STEP_DEFS[0][2], gateway_ok),
            auto_step("gateway_authenticated", AUTO_STEP_DEFS[1][1], AUTO_STEP_DEFS[1][2], authenticated),
            auto_step("harness_verified", AUTO_STEP_DEFS[2][1], AUTO_STEP_DEFS[2][2], account_visible),
        ]
    )
    completed_count = len([step for step in steps if step["completed"]])
    next_required = next((step["label"] for step in steps if not step["completed"]), None)
    return {
        "path": str(STATUS_PATH.relative_to(PROJECT_ROOT)),
        "updated_at": payload.get("updated_at"),
        "owner_note": payload.get("owner_note"),
        "steps": steps,
        "completed_count": completed_count,
        "total_count": len(steps),
        "next_required": next_required,
    }


def _find_manual_step(payload: dict[str, Any], step_id: str) -> dict[str, Any]:
    items = payload.setdefault("steps", [])
    for row in items:
        if str(row.get("id")) == step_id:
            return row
    valid_steps = ", ".join(step[0] for step in MANUAL_STEP_DEFS)
    raise SystemExit(f"unknown manual IBKR onboarding step: {step_id}. valid: {valid_steps}")


def command_status(args: argparse.Namespace) -> None:
    from scripts.ibkr_cp_client import IbkrCpClient, safe_check_connectivity

    preflight = safe_check_connectivity()
    auth = preflight.get("auth") or {}
    accounts_payload: dict[str, Any] = {"count": 0, "accounts": [], "error": None}
    if preflight.get("ok") and auth.get("authenticated") is True:
        client = IbkrCpClient()
        try:
            raw_accounts = client.accounts()
            account_rows = raw_accounts.get("accounts") if isinstance(raw_accounts, dict) else []
            if not isinstance(account_rows, list):
                account_rows = raw_accounts.get("data") if isinstance(raw_accounts, dict) else []
            accounts_payload = {"count": len(account_rows or []), "accounts": account_rows[:10], "error": None}
        except Exception as exc:
            accounts_payload = {"count": 0, "accounts": [], "error": str(exc)}
        finally:
            client.close()

    payload = {
        "preflight": {
            "ok": bool(preflight.get("ok")),
            "authenticated": auth.get("authenticated"),
            "base_url": preflight.get("base_url"),
            "tls_verify": preflight.get("tls_verify"),
            "error": preflight.get("error"),
        },
        "accounts": accounts_payload,
        "onboarding": compute_status(preflight, accounts_payload),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def command_complete(args: argparse.Namespace) -> None:
    payload = load_status_file()
    step = _find_manual_step(payload, args.step_id)
    step["completed"] = True
    if args.note:
        step["note"] = args.note
    save_status_file(payload)
    print(json.dumps({"ok": True, "action": "complete", "step_id": args.step_id, "path": str(STATUS_PATH)}, ensure_ascii=False, indent=2))


def command_reset(args: argparse.Namespace) -> None:
    payload = load_status_file()
    step = _find_manual_step(payload, args.step_id)
    step["completed"] = False
    if args.note:
        step["note"] = args.note
    save_status_file(payload)
    print(json.dumps({"ok": True, "action": "reset", "step_id": args.step_id, "path": str(STATUS_PATH)}, ensure_ascii=False, indent=2))


def command_note(args: argparse.Namespace) -> None:
    payload = load_status_file()
    payload["owner_note"] = args.note
    save_status_file(payload)
    print(json.dumps({"ok": True, "action": "note", "path": str(STATUS_PATH)}, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage IBKR onboarding status and preflight.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="show merged onboarding + gateway status")
    status_parser.set_defaults(func=command_status)

    complete_parser = subparsers.add_parser("complete", help="mark a manual onboarding step complete")
    complete_parser.add_argument("--step-id", required=True)
    complete_parser.add_argument("--note", default=None)
    complete_parser.set_defaults(func=command_complete)

    reset_parser = subparsers.add_parser("reset", help="mark a manual onboarding step incomplete")
    reset_parser.add_argument("--step-id", required=True)
    reset_parser.add_argument("--note", default=None)
    reset_parser.set_defaults(func=command_reset)

    note_parser = subparsers.add_parser("note", help="update the owner note")
    note_parser.add_argument("--note", required=True)
    note_parser.set_defaults(func=command_note)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
