from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = PROJECT_ROOT / "docs/trading/trading_watchlist_v0.json"


def _load_watchlist() -> dict[str, Any]:
    if not WATCHLIST_PATH.exists():
        return {
            "version": "v0",
            "generated_at": datetime.now().date().isoformat(),
            "policy": {
                "phase": "phase1",
                "notes": [
                    "Operator-facing trading watchlist.",
                    "Items may exist before IBKR registry approval.",
                ],
            },
            "items": [],
        }
    return json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))


def _save_watchlist(payload: dict[str, Any]) -> None:
    payload["generated_at"] = datetime.now().date().isoformat()
    WATCHLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _find_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for item in items:
        if str(item.get("id")) == item_id:
            return item
    return None


def command_list(_: argparse.Namespace) -> None:
    payload = _load_watchlist()
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def command_add(args: argparse.Namespace) -> None:
    payload = _load_watchlist()
    items = payload.setdefault("items", [])
    existing = _find_item(items, args.id)
    row = {
        "id": args.id,
        "active": True if existing is None else existing.get("active", True),
        "priority": args.priority,
        "watch_reason": args.watch_reason,
        "query": args.query,
        "exchange_hint": args.exchange_hint,
        "name_hint": args.name_hint,
        "region": args.region,
    }
    if existing:
        existing.update({k: v for k, v in row.items() if v is not None})
    else:
        items.append(row)
    items.sort(key=lambda item: (item.get("priority") is None, item.get("priority", 9999), str(item.get("id"))))
    _save_watchlist(payload)
    print(json.dumps({"ok": True, "action": "add", "id": args.id, "path": str(WATCHLIST_PATH)}, ensure_ascii=False, indent=2))


def command_deactivate(args: argparse.Namespace) -> None:
    payload = _load_watchlist()
    items = payload.setdefault("items", [])
    existing = _find_item(items, args.id)
    if not existing:
        raise SystemExit(f"watchlist item not found: {args.id}")
    existing["active"] = False
    _save_watchlist(payload)
    print(json.dumps({"ok": True, "action": "deactivate", "id": args.id, "path": str(WATCHLIST_PATH)}, ensure_ascii=False, indent=2))


def command_activate(args: argparse.Namespace) -> None:
    payload = _load_watchlist()
    items = payload.setdefault("items", [])
    existing = _find_item(items, args.id)
    if not existing:
        raise SystemExit(f"watchlist item not found: {args.id}")
    existing["active"] = True
    _save_watchlist(payload)
    print(json.dumps({"ok": True, "action": "activate", "id": args.id, "path": str(WATCHLIST_PATH)}, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage docs/trading/trading_watchlist_v0.json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="print current trading watchlist")
    list_parser.set_defaults(func=command_list)

    add_parser = subparsers.add_parser("add", help="add or update a trading watchlist item")
    add_parser.add_argument("--id", required=True)
    add_parser.add_argument("--query", required=True)
    add_parser.add_argument("--name-hint", required=True)
    add_parser.add_argument("--exchange-hint", required=False, default=None)
    add_parser.add_argument("--region", required=False, default=None)
    add_parser.add_argument("--priority", type=int, default=999)
    add_parser.add_argument("--watch-reason", required=False, default=None)
    add_parser.set_defaults(func=command_add)

    deactivate_parser = subparsers.add_parser("deactivate", help="mark a watchlist item inactive")
    deactivate_parser.add_argument("--id", required=True)
    deactivate_parser.set_defaults(func=command_deactivate)

    activate_parser = subparsers.add_parser("activate", help="mark a watchlist item active")
    activate_parser.add_argument("--id", required=True)
    activate_parser.set_defaults(func=command_activate)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
