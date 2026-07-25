from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from core.smartfarm_dashboard import SmartfarmRuntime


class _PublishResult:
    rc = 0


class _FakeMqtt:
    def __init__(self):
        self.calls: list[tuple[str, dict, int, bool]] = []

    def publish(self, topic: str, payload: str, qos: int, retain: bool):
        self.calls.append((topic, json.loads(payload), qos, retain))
        return _PublishResult()


class SmartfarmRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.runtime = SmartfarmRuntime(Path(self.temp_dir.name) / "ops.db")
        self.runtime.start()

    def tearDown(self):
        self.runtime.flush()
        self.temp_dir.cleanup()

    def _heartbeat(self, **overrides):
        payload = {
            "device_id": "esp32-zone1",
            "kind": "esp32",
            "board": "ESP32-D0WD-V3",
            "firmware": "smartfarm-node-2.0",
            "boot_id": "boot-1",
            "ip": "192.168.0.220",
            "rssi_dbm": -48,
            "uptime_s": 123,
            "watchdog_max_run_ms": 15000,
            "sensor_capabilities": ["dht22", "soil_adc"],
            "actuator_capabilities": ["pump_relay"],
            "state": "online",
            "ts": time.time(),
        }
        payload.update(overrides)
        self.runtime.ingest_message("farm/zone1/device/status", json.dumps(payload), retained=True)
        self.runtime.flush()

    def test_telemetry_to_overview_and_history(self):
        self._heartbeat()
        now = time.time()
        self.runtime.ingest_message(
            "farm/zone1/telemetry/soil_pct",
            json.dumps({"device_id": "esp32-zone1", "boot_id": "boot-1", "value": 42, "ts": now}),
        )
        self.runtime.ingest_message("farm/zone1/temp", "23.5")
        self.runtime.flush()

        overview = self.runtime.overview()
        self.assertEqual(overview["summary"]["devices"]["online"], 1)
        self.assertEqual(overview["zones"][0]["metrics"]["soil_pct"]["value"], 42)
        history = self.runtime.history("zone1", "soil_pct", 3600)
        self.assertEqual([point["value"] for point in history["points"]], [42])

    def test_lwt_offline_wins_even_when_retained(self):
        self._heartbeat()
        self.runtime.ingest_message(
            "farm/zone1/device/status",
            json.dumps({"device_id": "esp32-zone1", "state": "offline", "boot_id": "boot-1", "ts": time.time()}),
            retained=True,
        )
        self.runtime.flush()
        self.assertEqual(self.runtime.overview()["devices"][0]["health"], "offline")

    def test_out_of_range_reading_is_not_false_green(self):
        self.runtime.ingest_message("farm/zone1/humidity", "140")
        self.runtime.flush()
        metric = self.runtime.overview()["zones"][0]["metrics"]["humidity_pct"]
        self.assertEqual(metric["quality"], "out_of_range")

    def test_command_publish_is_pending_until_ack_and_observation(self):
        fake = _FakeMqtt()
        self.runtime.health.connected = True
        self.runtime._mqtt_client = fake
        command = self.runtime.create_command(
            zone_id="zone1",
            kind="pump_off",
            actor="ceo",
            params={"duration_s": 10},
        )
        self.assertEqual(command["status"], "published")
        self.assertFalse(fake.calls[0][3], "commands must never be retained")

        self.runtime.ingest_message(
            "farm/zone1/command/ack",
            json.dumps({"command_id": command["command_id"], "accepted": True, "phase": "acknowledged"}),
        )
        self.runtime.flush()
        self.assertEqual(self.runtime.command(command["command_id"])["status"], "acknowledged")

        self.runtime.ingest_message("farm/zone1/pump/status", "off", retained=True)
        self.runtime.flush()
        observed = self.runtime.command(command["command_id"])
        self.assertEqual(observed["status"], "observed")
        self.assertEqual(observed["observed_state"], "off")

    def test_on_gate_requires_feature_flag_fresh_watchdog_and_good_sensor(self):
        self._heartbeat()
        self.runtime.ingest_message("farm/zone1/soil_raw", "1700")
        self.runtime.flush()
        clear, reason, _ = self.runtime.pump_safety("zone1", 10)
        self.assertFalse(clear)
        self.assertEqual(reason, "actuation_disabled")

        with patch.dict(
            os.environ,
            {
                "HARNESS_SMARTFARM_ACTUATION_ENABLED": "true",
                "HARNESS_SMARTFARM_PUMP_CONTROL_ZONES": "zone1",
            },
        ):
            clear, reason, device_id = self.runtime.pump_safety("zone1", 10)
        self.assertTrue(clear)
        self.assertEqual(reason, "clear")
        self.assertEqual(device_id, "esp32-zone1")

    def test_pump_test_has_separate_flag_and_completes_only_after_auto_off(self):
        self._heartbeat(watchdog_max_run_ms=15000)
        self.runtime.ingest_message("farm/zone1/soil_raw", "1700")
        self.runtime.flush()
        with patch.dict(
            os.environ,
            {
                "HARNESS_SMARTFARM_PUMP_TEST_ENABLED": "true",
                "HARNESS_SMARTFARM_PUMP_CONTROL_ZONES": "zone1",
            },
        ):
            clear, reason, device_id = self.runtime.pump_safety("zone1", 3, test_mode=True)
        self.assertTrue(clear)
        self.assertEqual(reason, "clear")

        fake = _FakeMqtt()
        self.runtime.health.connected = True
        self.runtime._mqtt_client = fake
        command = self.runtime.create_command(
            zone_id="zone1",
            device_id=device_id,
            kind="pump_test",
            actor="ceo",
            params={"duration_s": 3},
        )
        self.runtime.ingest_message("farm/zone1/pump/status", "on")
        self.runtime.flush()
        self.assertEqual(self.runtime.command(command["command_id"])["status"], "running")
        self.runtime.ingest_message("farm/zone1/pump/status", "off")
        self.runtime.flush()
        completed = self.runtime.command(command["command_id"])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["observed_state"], "off")

    def test_configured_pump_zone_blocks_wrong_physical_zone(self):
        self._heartbeat()
        self.runtime.ingest_message("farm/zone1/soil_raw", "1700")
        self.runtime.flush()
        with patch.dict(
            os.environ,
            {
                "HARNESS_SMARTFARM_PUMP_TEST_ENABLED": "true",
                "HARNESS_SMARTFARM_PUMP_CONTROL_ZONES": "zone2",
            },
        ):
            clear, reason, device_id = self.runtime.pump_safety("zone1", 3, test_mode=True)
            overview = self.runtime.overview()
        self.assertFalse(clear)
        self.assertEqual(reason, "pump_control_zone_disabled")
        self.assertIsNone(device_id)
        self.assertEqual(overview["runtime"]["pump_control_zones"], ["zone2"])

    def test_missing_pump_zone_configuration_fails_closed(self):
        self._heartbeat()
        with patch.dict(
            os.environ,
            {
                "HARNESS_SMARTFARM_PUMP_TEST_ENABLED": "true",
                "HARNESS_SMARTFARM_PUMP_CONTROL_ZONES": "",
            },
        ):
            clear, reason, device_id = self.runtime.pump_safety("zone1", 3, test_mode=True)
        self.assertFalse(clear)
        self.assertEqual(reason, "pump_control_zones_not_configured")
        self.assertIsNone(device_id)

    def test_rejected_command_preserves_edge_safety_reason(self):
        fake = _FakeMqtt()
        self.runtime.health.connected = True
        self.runtime._mqtt_client = fake
        command = self.runtime.create_command(
            zone_id="zone1",
            kind="pump_test",
            actor="ceo",
            params={"duration_s": 3},
        )
        self.runtime.ingest_message(
            "farm/zone1/command/ack",
            json.dumps(
                {
                    "command_id": command["command_id"],
                    "accepted": False,
                    "phase": "rejected",
                    "reason": "active_or_cooldown",
                }
            ),
        )
        self.runtime.flush()
        rejected = self.runtime.command(command["command_id"])
        self.assertEqual(rejected["status"], "rejected")
        self.assertEqual(rejected["safety_reason"], "active_or_cooldown")

    def test_bounded_pump_on_completes_only_after_observed_auto_off(self):
        fake = _FakeMqtt()
        self.runtime.health.connected = True
        self.runtime._mqtt_client = fake
        command = self.runtime.create_command(
            zone_id="zone2",
            kind="pump_on",
            actor="ceo",
            params={"duration_s": 3},
        )
        self.runtime.ingest_message("farm/zone2/pump/status", "on")
        self.runtime.flush()
        running = self.runtime.command(command["command_id"])
        self.assertEqual(running["status"], "observed")
        self.assertEqual(running["observed_state"], "on")
        self.runtime.ingest_message("farm/zone2/pump/status", "off")
        self.runtime.flush()
        completed = self.runtime.command(command["command_id"])
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["observed_state"], "off")

    def test_pump_on_does_not_false_complete_from_off_before_on(self):
        fake = _FakeMqtt()
        self.runtime.health.connected = True
        self.runtime._mqtt_client = fake
        command = self.runtime.create_command(
            zone_id="zone2",
            kind="pump_on",
            actor="ceo",
            params={"duration_s": 3},
        )
        self.runtime.ingest_message("farm/zone2/pump/status", "off")
        self.runtime.flush()
        pending = self.runtime.command(command["command_id"])
        self.assertNotEqual(pending["status"], "completed")
        self.assertNotEqual(pending["observed_state"], "off")

    def test_invasive_diagnostic_requires_observed_off(self):
        clear, reason = self.runtime.diagnostic_safety("zone1", invasive=True)
        self.assertFalse(clear)
        self.assertEqual(reason, "invasive_test_requires_observed_pump_off")
        self.runtime.ingest_message("farm/zone1/pump/status", "off")
        self.runtime.flush()
        self.assertEqual(self.runtime.diagnostic_safety("zone1", invasive=True), (True, "clear"))

    def test_concurrent_ingest_reads_and_commands_do_not_lock_database(self):
        self._heartbeat()
        errors: list[Exception] = []

        def ingest():
            try:
                for value in range(200):
                    self.runtime.ingest_message("farm/zone1/soil", str(value % 101))
            except Exception as exc:  # pragma: no cover - assertion captures worker error
                errors.append(exc)

        def read_and_command():
            try:
                for _ in range(30):
                    self.runtime.overview()
                    self.runtime.create_command(
                        zone_id="zone1", kind="pump_off", actor="ceo", params={"duration_s": 5}
                    )
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        workers = [threading.Thread(target=ingest), threading.Thread(target=read_and_command)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.runtime.flush()
        self.assertEqual(errors, [])

    def test_failed_diagnostic_marks_device_fault_and_opens_alert(self):
        self._heartbeat()
        fake = _FakeMqtt()
        self.runtime.health.connected = True
        self.runtime._mqtt_client = fake
        command = self.runtime.create_command(
            zone_id="zone1",
            device_id="esp32-zone1",
            kind="diagnostic",
            actor="ceo",
            params={"checks": ["sensors"], "invasive": False},
        )
        self.runtime.ingest_message(
            "farm/zone1/diagnostic/result",
            json.dumps(
                {
                    "command_id": command["command_id"],
                    "accepted": True,
                    "phase": "result",
                    "dht22": {"pass": False},
                    "soil_adc": {"pass": True},
                }
            ),
        )
        self.runtime.flush()
        overview = self.runtime.overview()
        self.assertEqual(overview["devices"][0]["health"], "fault")
        self.assertEqual(overview["summary"]["alerts_open"], 1)
        self.assertEqual(overview["alerts"][0]["code"], "diagnostic_failed")
        self._heartbeat(state="online", ts=time.time() + 1)
        self.assertEqual(
            self.runtime.overview()["devices"][0]["health"],
            "fault",
            "fresh heartbeat must not hide an unresolved high-severity diagnostic alert",
        )


if __name__ == "__main__":
    unittest.main()
