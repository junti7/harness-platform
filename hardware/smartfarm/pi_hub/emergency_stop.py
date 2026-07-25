#!/usr/bin/env python3
"""Pi-local fail-safe pump shutdown.

Run directly on the Raspberry Pi when Harness OS or its authentication path is
unavailable. It only publishes OFF, never ON. The node watchdog remains the
last independent safety layer if MQTT itself is unavailable.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import yaml


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish fail-safe OFF to smartfarm zones")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.yaml")))
    parser.add_argument("--zone", action="append", help="Zone to stop; repeatable. Default: all configured zones")
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text())
    configured = sorted((config.get("zones") or {}).keys())
    targets = args.zone or configured
    unknown = sorted(set(targets) - set(configured))
    if unknown:
        parser.error(f"unknown zone(s): {', '.join(unknown)}")

    client = mqtt.Client(client_id=f"pi-emergency-stop-{int(time.time())}")
    client.connect(config["mqtt"]["host"], int(config["mqtt"].get("port", 1883)), keepalive=15)
    client.loop_start()
    try:
        for zone_id in targets:
            info = client.publish(f"farm/{zone_id}/pump/cmd", "off", qos=1, retain=False)
            info.wait_for_publish(timeout=3)
            if not info.is_published():
                raise RuntimeError(f"OFF publish not confirmed for {zone_id}")
            print(f"[emergency-stop] OFF published: {zone_id}")
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
