from __future__ import annotations

import argparse
import json
import socket
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATUS_PATH = PROJECT_ROOT / "docs" / "reports" / "ibkr_gateway_runtime_status.json"
GATEWAY_PORT = 4002
VALID_STATUSES = {"offline", "launching", "waiting_for_2fa", "ready"}


def _iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _check_port_open() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", GATEWAY_PORT), timeout=1.0):
            return True
    except OSError:
        return False


def load_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return {
            "status": "offline",
            "message": "IB Gateway가 실행되지 않았습니다.",
            "source": "default",
            "updated_at": _iso_now(),
            "port_open": False,
            "wait_timeout_sec": 120,
        }
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "status": "offline",
            "message": "IB Gateway 상태 파일을 읽지 못했습니다.",
            "source": "default",
            "updated_at": _iso_now(),
            "port_open": False,
            "wait_timeout_sec": 120,
        }


def save_status(
    *,
    status: str,
    message: str,
    source: str,
    port_open: bool | None = None,
    wait_timeout_sec: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    payload = load_status()
    payload.update(
        {
            "status": status,
            "message": message,
            "source": source,
            "updated_at": _iso_now(),
            "port_open": _check_port_open() if port_open is None else bool(port_open),
        }
    )
    if wait_timeout_sec is not None:
        payload["wait_timeout_sec"] = int(wait_timeout_sec)
    if details is not None:
        payload["details"] = details
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Write/read IB Gateway runtime status.")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES))
    parser.add_argument("--message")
    parser.add_argument("--source", default="manual")
    parser.add_argument("--port-open", choices=["true", "false"])
    parser.add_argument("--wait-timeout-sec", type=int)
    parser.add_argument("--print", dest="print_only", action="store_true")
    args = parser.parse_args()

    if args.print_only or not args.status:
        print(json.dumps(load_status(), ensure_ascii=False, indent=2))
        return

    payload = save_status(
        status=args.status,
        message=args.message or "",
        source=args.source,
        port_open=None if args.port_open is None else args.port_open == "true",
        wait_timeout_sec=args.wait_timeout_sec,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
