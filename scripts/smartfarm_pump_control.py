#!/usr/bin/env python3
"""Safety-bounded MQTT pump command used only by the OpenClaw native tool."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import time
from typing import Any

DEFAULT_BROKER = "192.168.0.23"
DEFAULT_PORT = 1883
MAX_ON_SECONDS = 15
ZONE_RE = re.compile(r"^zone[1-9][0-9]{0,2}$")


def _remaining_length(value: int) -> bytes:
    encoded = bytearray()
    while True:
        digit = value % 128
        value //= 128
        if value:
            digit |= 0x80
        encoded.append(digit)
        if not value:
            return bytes(encoded)


def _utf8(value: str) -> bytes:
    raw = value.encode("utf-8")
    return len(raw).to_bytes(2, "big") + raw


def _send_packet(sock: socket.socket, packet_type: int, payload: bytes) -> None:
    sock.sendall(bytes([packet_type]) + _remaining_length(len(payload)) + payload)


def _connect(host: str, port: int) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=3)
    sock.settimeout(3)
    variable_header = _utf8("MQTT") + bytes([4, 2]) + (15).to_bytes(2, "big")
    client_id = f"openclaw-pump-{os.getpid()}-{int(time.time())}"
    _send_packet(sock, 0x10, variable_header + _utf8(client_id))
    connack = sock.recv(4)
    if len(connack) != 4 or connack[:3] != b"\x20\x02\x00" or connack[3] != 0:
        sock.close()
        raise RuntimeError(f"mqtt_connack_failed:{connack.hex()}")
    return sock


def _publish(sock: socket.socket, topic: str, value: str) -> None:
    packet_id = b"\x00\x01"
    _send_packet(sock, 0x32, _utf8(topic) + packet_id + value.encode("utf-8"))
    puback = sock.recv(4)
    if puback != b"\x40\x02\x00\x01":
        raise RuntimeError(f"mqtt_puback_failed:{puback.hex()}")


def _disconnect(sock: socket.socket) -> None:
    try:
        sock.sendall(b"\xe0\x00")
    finally:
        sock.close()


def publish_once(host: str, port: int, topic: str, value: str) -> None:
    sock = _connect(host, port)
    try:
        _publish(sock, topic, value)
    finally:
        _disconnect(sock)


def control_pump(
    *,
    zone: str,
    action: str,
    confirmed: bool,
    duration_seconds: int,
    broker: str = DEFAULT_BROKER,
    port: int = DEFAULT_PORT,
    dry_run: bool = False,
) -> dict[str, Any]:
    if not ZONE_RE.fullmatch(zone):
        raise ValueError("invalid_zone")
    if action not in {"on", "off"}:
        raise ValueError("invalid_action")
    if action == "on" and not confirmed:
        raise PermissionError("explicit_confirmation_required")
    if not 1 <= duration_seconds <= MAX_ON_SECONDS:
        raise ValueError(f"duration_must_be_1_to_{MAX_ON_SECONDS}")

    topic = f"farm/{zone}/pump/cmd"
    result: dict[str, Any] = {
        "ok": True,
        "zone": zone,
        "action": action,
        "topic": topic,
        "broker": broker,
        "dryRun": dry_run,
    }
    if dry_run:
        result["commands"] = ["off"] if action == "off" else ["on", "off"]
        result["autoOffSeconds"] = duration_seconds if action == "on" else 0
        return result

    if action == "on":
        raise PermissionError("on_blocked_until_independent_hardware_watchdog_is_verified")

    errors: list[str] = []
    for _attempt in range(3):
        try:
            publish_once(broker, port, topic, "off")
            result["commandState"] = "off_published_broker_acknowledged"
            result["physicalStateVerified"] = False
            result["publishAttempts"] = len(errors) + 1
            return result
        except (OSError, RuntimeError) as exc:
            errors.append(f"{type(exc).__name__}:{exc}")
    raise RuntimeError(f"off_publish_failed_after_3_attempts:{' | '.join(errors)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zone", required=True)
    parser.add_argument("--action", choices=["on", "off"], required=True)
    parser.add_argument("--confirmed", action="store_true")
    parser.add_argument("--duration-seconds", type=int, default=5)
    parser.add_argument("--broker", default=DEFAULT_BROKER)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        result = control_pump(
            zone=args.zone,
            action=args.action,
            confirmed=args.confirmed,
            duration_seconds=args.duration_seconds,
            broker=args.broker,
            port=args.port,
            dry_run=args.dry_run,
        )
    except (OSError, PermissionError, RuntimeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
