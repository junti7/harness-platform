from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from hardware.smartfarm.pi_hub.hub import SmartfarmHub


class FakeClient:
    def __init__(self):
        self.published: list[tuple[str, str, int, bool]] = []

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        self.published.append((topic, payload, qos, retain))


def _hub(tmp_path: Path) -> tuple[SmartfarmHub, FakeClient]:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("zones: {}")
    config = {
        "db_path": str(tmp_path / "hub.db"),
        "zones": {
            "zone1": {
                "soil_min_pct": 30,
                "soil_target_pct": 60,
                "water_duration_s": 10,
                "cooldown_s": 0,
            }
        },
    }
    hub = SmartfarmHub(config, config_path)
    client = FakeClient()
    hub.client = client
    return hub, client


def test_manual_on_flows_through_hub_state_and_ack(tmp_path: Path) -> None:
    hub, client = _hub(tmp_path)
    command = {
        "command_id": "cmd-1",
        "kind": "pump_on",
        "sequence": 1,
        "expires_at": time.time() + 20,
        "params": {"duration_s": 5},
    }
    hub._handle_manual_command("zone1", json.dumps(command))
    assert hub.zones["zone1"].pump_on is True
    assert ("farm/zone1/pump/cmd", "on", 1, False) in client.published
    ack = next(json.loads(payload) for topic, payload, _, _ in client.published if topic.endswith("/command/ack"))
    assert ack["accepted"] is True
    hub._stop_pump(hub.zones["zone1"], None, "test_cleanup")


def test_expired_or_replayed_manual_command_is_rejected(tmp_path: Path) -> None:
    hub, client = _hub(tmp_path)
    expired = {
        "command_id": "cmd-expired",
        "kind": "pump_on",
        "sequence": 1,
        "expires_at": time.time() - 1,
        "params": {"duration_s": 5},
    }
    hub._handle_manual_command("zone1", json.dumps(expired))
    assert hub.zones["zone1"].pump_on is False
    assert not any(topic.endswith("/pump/cmd") for topic, *_ in client.published)
    ack = json.loads(client.published[-1][1])
    assert ack["accepted"] is False
    assert ack["reason"] == "expired"


def test_firmware_allocates_buffer_for_heartbeat_and_diagnostic_json() -> None:
    source = Path("hardware/smartfarm/soil_node/soil_node.ino").read_text()
    assert "mqtt.setBufferSize(1024)" in source
