"""Smartfarm operational store and MQTT runtime for Harness OS.

The module deliberately keeps physical state separate from command intent:
publishing is never reported as success until an edge acknowledgement and an
observed pump status arrive. MQTT is optional so the API can still expose an
honest disconnected dashboard during local development or broker outages.
"""
from __future__ import annotations

import json
import os
import queue
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import paho.mqtt.client as mqtt
except ImportError:  # pragma: no cover - optional in unit-test environments
    mqtt = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS smartfarm_devices (
    device_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    zone_id TEXT,
    board TEXT,
    firmware TEXT,
    boot_id TEXT,
    ip TEXT,
    rssi_dbm REAL,
    uptime_s REAL,
    watchdog_max_run_ms INTEGER,
    capabilities_json TEXT NOT NULL DEFAULT '{}',
    state TEXT NOT NULL DEFAULT 'unknown',
    source_ts REAL,
    last_seen_at REAL NOT NULL,
    last_payload_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_smartfarm_devices_zone ON smartfarm_devices(zone_id);
CREATE INDEX IF NOT EXISTS idx_smartfarm_devices_seen ON smartfarm_devices(last_seen_at);

CREATE TABLE IF NOT EXISTS smartfarm_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    zone_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    quality TEXT NOT NULL DEFAULT 'good',
    source_ts REAL,
    boot_id TEXT NOT NULL DEFAULT '',
    ingested_at REAL NOT NULL,
    UNIQUE(device_id, metric, source_ts, boot_id)
);
CREATE INDEX IF NOT EXISTS idx_smartfarm_readings_lookup
    ON smartfarm_readings(zone_id, metric, ingested_at);

CREATE TABLE IF NOT EXISTS smartfarm_commands (
    command_id TEXT PRIMARY KEY,
    device_id TEXT,
    zone_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    params_json TEXT NOT NULL,
    actor TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    status TEXT NOT NULL,
    safety_reason TEXT,
    issued_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    published_at REAL,
    ack_at REAL,
    observed_at REAL,
    observed_state TEXT,
    detail_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_smartfarm_commands_zone_time
    ON smartfarm_commands(zone_id, issued_at DESC);

CREATE TABLE IF NOT EXISTS smartfarm_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    severity TEXT NOT NULL,
    device_id TEXT,
    zone_id TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    message TEXT NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    opened_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(code, device_id, zone_id, status)
);

CREATE TABLE IF NOT EXISTS smartfarm_runtime_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '{}',
    recorded_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS smartfarm_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

LEGACY_METRICS = {
    "soil": "soil_pct",
    "soil_raw": "soil_raw",
    "temp": "temp_c",
    "humidity": "humidity_pct",
}
VALID_METRICS = set(LEGACY_METRICS.values()) | {"light_lux", "water_level_pct", "flow_lpm"}


def _now() -> float:
    return time.time()


def _iso(value: float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _safe_json(raw: str | None, fallback: Any) -> Any:
    try:
        return json.loads(raw or "")
    except (TypeError, ValueError):
        return fallback


@dataclass
class RuntimeHealth:
    configured: bool = False
    connected: bool = False
    last_connect_at: float | None = None
    last_disconnect_at: float | None = None
    last_message_at: float | None = None
    error: str | None = None


class SmartfarmRuntime:
    def __init__(self, db_path: Path, *, mqtt_host: str = "", mqtt_port: int = 1883):
        self.db_path = db_path
        self.mqtt_host = mqtt_host.strip()
        self.mqtt_port = int(mqtt_port)
        self.stale_after_s = max(15, int(os.getenv("HARNESS_SMARTFARM_STALE_AFTER_S", "90")))
        self.offline_after_s = max(self.stale_after_s + 1, int(os.getenv("HARNESS_SMARTFARM_OFFLINE_AFTER_S", "180")))
        self.health = RuntimeHealth(configured=bool(self.mqtt_host))
        self._db_lock = threading.Lock()
        self._write_queue: queue.Queue[tuple[str, tuple[Any, ...]] | None] = queue.Queue(maxsize=10000)
        self._writer_thread: threading.Thread | None = None
        self._mqtt_client: Any = None
        self._started = False
        self._sequence_lock = threading.Lock()
        self._control_locks: dict[str, threading.Lock] = {}
        self._control_locks_guard = threading.Lock()
        self._init_db()

    def _connect(self, readonly: bool = False) -> sqlite3.Connection:
        if readonly:
            uri = f"file:{self.db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=5)
        else:
            conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(SCHEMA)

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._writer_thread = threading.Thread(target=self._writer_loop, name="smartfarm-db-writer", daemon=True)
        self._writer_thread.start()
        if not self.mqtt_host:
            self.health.error = "HARNESS_SMARTFARM_MQTT_HOST not configured"
            return
        if mqtt is None:
            self.health.error = "paho-mqtt is not installed"
            return
        try:
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=f"harness-os-{os.getpid()}")
            except (AttributeError, TypeError):
                client = mqtt.Client(client_id=f"harness-os-{os.getpid()}")
            username = os.getenv("HARNESS_SMARTFARM_MQTT_USERNAME", "").strip()
            password = os.getenv("HARNESS_SMARTFARM_MQTT_PASSWORD", "")
            if username:
                client.username_pw_set(username, password)
            ca_path = os.getenv("HARNESS_SMARTFARM_MQTT_CA_PATH", "").strip()
            if ca_path:
                client.tls_set(ca_certs=ca_path)
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            client.connect_async(self.mqtt_host, self.mqtt_port, keepalive=30)
            client.loop_start()
            self._mqtt_client = client
        except Exception as exc:  # noqa: BLE001 - expose degraded health, do not crash Harness OS
            self.health.error = f"{type(exc).__name__}: {exc}"
            self._runtime_event("mqtt_start_failed", {"error": self.health.error})

    def _writer_loop(self) -> None:
        while True:
            item = self._write_queue.get()
            if item is None:
                return
            statement, params = item
            try:
                with self._db_lock:
                    with self._connect() as conn:
                        conn.execute(statement, params)
            except Exception as exc:  # noqa: BLE001
                self.health.error = f"database writer: {type(exc).__name__}: {exc}"
            finally:
                self._write_queue.task_done()

    def _enqueue(self, statement: str, params: tuple[Any, ...]) -> None:
        try:
            self._write_queue.put_nowait((statement, params))
        except queue.Full:
            self.health.error = "database writer queue full; telemetry dropped"

    def flush(self, timeout_s: float = 3.0) -> bool:
        deadline = time.monotonic() + timeout_s
        while self._write_queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.01)
        return self._write_queue.unfinished_tasks == 0

    def _runtime_event(self, event_type: str, detail: dict[str, Any]) -> None:
        self._enqueue(
            "INSERT INTO smartfarm_runtime_events(event_type, detail_json, recorded_at) VALUES(?,?,?)",
            (event_type, _json(detail), _now()),
        )

    def _on_connect(self, client: Any, userdata: Any, flags: Any, rc: int) -> None:
        self.health.connected = rc == 0
        self.health.last_connect_at = _now()
        self.health.error = None if rc == 0 else f"MQTT connect rc={rc}"
        if rc != 0:
            return
        for topic in (
            "farm/+/soil",
            "farm/+/soil_raw",
            "farm/+/temp",
            "farm/+/humidity",
            "farm/+/telemetry/+",
            "farm/+/pump/status",
            "farm/+/device/status",
            "farm/+/command/ack",
            "farm/+/diagnostic/result",
            "farm/system/pi-hub/status",
        ):
            client.subscribe(topic, qos=1)
        self._runtime_event("mqtt_connected", {"host": self.mqtt_host, "port": self.mqtt_port})

    def _on_disconnect(self, client: Any, userdata: Any, rc: int) -> None:
        self.health.connected = False
        self.health.last_disconnect_at = _now()
        self.health.error = f"MQTT disconnected rc={rc}"
        self._runtime_event("mqtt_disconnected", {"rc": rc})

    def _on_message(self, client: Any, userdata: Any, msg: Any) -> None:
        self.health.last_message_at = _now()
        payload = msg.payload.decode("utf-8", errors="replace")
        self.ingest_message(msg.topic, payload, retained=bool(getattr(msg, "retain", False)))

    def ingest_message(self, topic: str, payload: str, *, retained: bool = False) -> None:
        """Validate and reduce one MQTT message. Public for deterministic replay tests."""
        if len(topic) > 200 or len(payload.encode("utf-8")) > 16_384:
            self._runtime_event("message_rejected", {"reason": "size", "topic": topic[:200]})
            return
        parts = topic.split("/")
        received_at = _now()
        if topic == "farm/system/pi-hub/status":
            data = _safe_json(payload, {})
            if isinstance(data, dict):
                data.setdefault("device_id", "pi-hub")
                data.setdefault("kind", "raspberry_pi")
                self._upsert_device(data, zone_id=None, received_at=received_at)
            return
        if len(parts) < 3 or parts[0] != "farm":
            return
        zone_id = parts[1]
        if not zone_id or len(zone_id) > 64 or not all(ch.isalnum() or ch in "_-" for ch in zone_id):
            return
        suffix = "/".join(parts[2:])
        if suffix == "device/status":
            data = _safe_json(payload, {})
            if isinstance(data, dict):
                self._upsert_device(data, zone_id=zone_id, received_at=received_at)
            return
        if suffix == "command/ack" or suffix == "diagnostic/result":
            data = _safe_json(payload, {})
            if isinstance(data, dict):
                self._apply_ack(zone_id, data, diagnostic=suffix.startswith("diagnostic"))
            return
        if suffix == "pump/status":
            state = payload.strip().lower()
            if state in {"on", "off"}:
                self._record_pump_observation(zone_id, state, received_at)
            return
        metric = LEGACY_METRICS.get(parts[2])
        if parts[2] == "telemetry" and len(parts) == 4:
            metric = parts[3]
        if metric in VALID_METRICS:
            data = _safe_json(payload, None)
            if isinstance(data, dict):
                value = data.get("value")
                source_ts = self._coerce_timestamp(data.get("ts"))
                device_id = str(data.get("device_id") or f"{zone_id}-node")
                boot_id = str(data.get("boot_id") or "")
                quality = str(data.get("quality") or "good")
            else:
                value = payload
                source_ts = received_at
                device_id = f"{zone_id}-node"
                boot_id = ""
                quality = "good"
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return
            if not self._metric_value_valid(metric, numeric):
                quality = "out_of_range"
            self._enqueue(
                """INSERT OR IGNORE INTO smartfarm_readings
                   (device_id,zone_id,metric,value,quality,source_ts,boot_id,ingested_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (device_id[:128], zone_id, metric, numeric, quality[:32], source_ts, boot_id[:128], received_at),
            )

    @staticmethod
    def _coerce_timestamp(value: Any) -> float:
        try:
            timestamp = float(value)
        except (TypeError, ValueError):
            return _now()
        return timestamp / 1000 if timestamp > 10_000_000_000 else timestamp

    @staticmethod
    def _metric_value_valid(metric: str, value: float) -> bool:
        ranges = {
            "soil_pct": (0, 100),
            "soil_raw": (0, 65535),
            "temp_c": (-40, 85),
            "humidity_pct": (0, 100),
            "light_lux": (0, 500000),
            "water_level_pct": (0, 100),
            "flow_lpm": (0, 1000),
        }
        low, high = ranges[metric]
        return low <= value <= high

    def _upsert_device(self, data: dict[str, Any], *, zone_id: str | None, received_at: float) -> None:
        device_id = str(data.get("device_id") or (f"{zone_id}-node" if zone_id else "pi-hub"))[:128]
        state = str(data.get("state") or "online").lower()
        if state not in {"online", "offline", "fault", "unknown"}:
            state = "unknown"
        kind = str(data.get("kind") or self._infer_kind(data))[:32]
        capabilities = {
            "sensors": data.get("sensor_capabilities") or [],
            "actuators": data.get("actuator_capabilities") or [],
        }
        source_ts = self._coerce_timestamp(data.get("ts"))
        self._enqueue(
            """INSERT INTO smartfarm_devices
               (device_id,kind,zone_id,board,firmware,boot_id,ip,rssi_dbm,uptime_s,
                watchdog_max_run_ms,capabilities_json,state,source_ts,last_seen_at,last_payload_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(device_id) DO UPDATE SET
                kind=excluded.kind,zone_id=excluded.zone_id,board=excluded.board,
                firmware=excluded.firmware,boot_id=excluded.boot_id,ip=excluded.ip,
                rssi_dbm=excluded.rssi_dbm,uptime_s=excluded.uptime_s,
                watchdog_max_run_ms=excluded.watchdog_max_run_ms,
                capabilities_json=excluded.capabilities_json,state=excluded.state,
                source_ts=excluded.source_ts,last_seen_at=excluded.last_seen_at,
                last_payload_json=excluded.last_payload_json""",
            (
                device_id,
                kind,
                zone_id,
                str(data.get("board") or "")[:80],
                str(data.get("firmware") or "")[:80],
                str(data.get("boot_id") or "")[:128],
                str(data.get("ip") or "")[:64],
                data.get("rssi_dbm"),
                data.get("uptime_s"),
                data.get("watchdog_max_run_ms"),
                _json(capabilities),
                state,
                source_ts,
                received_at,
                _json(data),
            ),
        )

    @staticmethod
    def _infer_kind(data: dict[str, Any]) -> str:
        board = str(data.get("board") or "").lower()
        if "8266" in board:
            return "esp8266"
        if "esp32" in board:
            return "esp32"
        if "raspberry" in board or "pi" in board:
            return "raspberry_pi"
        return "edge_node"

    def _apply_ack(self, zone_id: str, data: dict[str, Any], *, diagnostic: bool) -> None:
        command_id = str(data.get("command_id") or "")
        if not command_id:
            return
        accepted = bool(data.get("accepted", True))
        phase = str(data.get("phase") or ("completed" if diagnostic else "acknowledged"))
        status = "rejected" if not accepted else ("completed" if phase in {"completed", "result"} else "acknowledged")
        safety_reason = str(data.get("reason") or "") if not accepted else None
        self._enqueue(
            """UPDATE smartfarm_commands SET status=?, safety_reason=?, ack_at=?, detail_json=?
               WHERE command_id=? AND zone_id=?""",
            (status, safety_reason, _now(), _json(data), command_id, zone_id),
        )
        if diagnostic and accepted and phase in {"completed", "result"}:
            self._apply_diagnostic_health(command_id, zone_id, data)

    def _apply_diagnostic_health(
        self, command_id: str, zone_id: str, data: dict[str, Any]
    ) -> None:
        with self._connect(readonly=True) as conn:
            row = conn.execute(
                "SELECT device_id FROM smartfarm_commands WHERE command_id=? AND zone_id=?",
                (command_id, zone_id),
            ).fetchone()
        device_id = str(row["device_id"] or "") if row else ""
        if not device_id:
            return
        failures = [
            name
            for name, result in data.items()
            if isinstance(result, dict) and result.get("pass") is False
        ]
        now = _now()
        if failures:
            message = f"Self-test failed: {', '.join(sorted(failures))}"
            self._enqueue(
                "UPDATE smartfarm_devices SET state='fault' WHERE device_id=?",
                (device_id,),
            )
            self._enqueue(
                """INSERT INTO smartfarm_alerts
                   (code,severity,device_id,zone_id,status,message,evidence_json,opened_at,updated_at)
                   VALUES('diagnostic_failed','high',?,?,'open',?,?,?,?)
                   ON CONFLICT(code,device_id,zone_id,status) DO UPDATE SET
                    message=excluded.message,evidence_json=excluded.evidence_json,updated_at=excluded.updated_at""",
                (device_id, zone_id, message, _json({"command_id": command_id, "failures": failures}), now, now),
            )
        else:
            self._enqueue(
                """UPDATE smartfarm_alerts SET status='resolved',updated_at=?
                   WHERE code='diagnostic_failed' AND device_id=? AND zone_id=? AND status='open'""",
                (now, device_id, zone_id),
            )
            self._enqueue(
                "UPDATE smartfarm_devices SET state='online' WHERE device_id=? AND state='fault'",
                (device_id,),
            )

    def _record_pump_observation(self, zone_id: str, state: str, observed_at: float) -> None:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT command_id,kind FROM smartfarm_commands
                   WHERE zone_id=? AND kind IN ('pump_on','pump_off','pump_test')
                   AND status IN ('published','acknowledged','running','unknown')
                   ORDER BY issued_at DESC LIMIT 1""",
                (zone_id,),
            ).fetchone()
        if row:
            if row["kind"] == "pump_test" and state == "on":
                self._enqueue(
                    """UPDATE smartfarm_commands SET status='running',observed_at=?,observed_state='on'
                       WHERE command_id=?""",
                    (observed_at, row["command_id"]),
                )
            elif (row["kind"] == "pump_test" and state == "off") or row["kind"] == f"pump_{state}":
                final_status = "completed" if row["kind"] == "pump_test" else "observed"
                self._enqueue(
                    """UPDATE smartfarm_commands SET status=?, observed_at=?, observed_state=?
                       WHERE command_id=?""",
                    (final_status, observed_at, state, row["command_id"]),
                )
        self._enqueue(
            """INSERT OR REPLACE INTO smartfarm_meta(key,value) VALUES(?,?)""",
            (f"pump:{zone_id}", _json({"state": state, "observed_at": observed_at})),
        )

    def _next_sequence(self) -> int:
        with self._sequence_lock, self._db_lock:
            with self._connect() as conn:
                row = conn.execute("SELECT value FROM smartfarm_meta WHERE key='command_sequence'").fetchone()
                value = int(row["value"]) + 1 if row else 1
                conn.execute(
                    "INSERT OR REPLACE INTO smartfarm_meta(key,value) VALUES('command_sequence',?)",
                    (str(value),),
                )
                return value

    @contextmanager
    def control_guard(self, zone_id: str):
        """Serialize safety-check + command creation for one physical zone."""
        with self._control_locks_guard:
            lock = self._control_locks.setdefault(zone_id, threading.Lock())
        with lock:
            yield

    def create_command(
        self,
        *,
        zone_id: str,
        kind: str,
        actor: str,
        params: dict[str, Any],
        device_id: str | None = None,
    ) -> dict[str, Any]:
        command_id = str(uuid4())
        issued_at = _now()
        expires_at = issued_at + 20
        sequence = self._next_sequence()
        command = {
            "command_id": command_id,
            "kind": kind,
            "sequence": sequence,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "params": params,
        }
        with self._db_lock:
            with self._connect() as conn:
                conn.execute(
                    """INSERT INTO smartfarm_commands
                       (command_id,device_id,zone_id,kind,params_json,actor,sequence,status,issued_at,expires_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (command_id, device_id, zone_id, kind, _json(params), actor, sequence, "created", issued_at, expires_at),
                )
        if not self.health.connected or self._mqtt_client is None:
            with self._db_lock:
                with self._connect() as conn:
                    conn.execute(
                        "UPDATE smartfarm_commands SET status='blocked',safety_reason=? WHERE command_id=?",
                        ("mqtt_not_connected", command_id),
                    )
            return self.command(command_id)
        suffix = "diagnostic/request" if kind == "diagnostic" else "command/request"
        result = self._mqtt_client.publish(f"farm/{zone_id}/{suffix}", _json(command), qos=1, retain=False)
        rc = int(getattr(result, "rc", 0))
        status = "published" if rc == 0 else "failed"
        with self._db_lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE smartfarm_commands SET status=?,published_at=?,safety_reason=? WHERE command_id=?",
                    (status, _now() if rc == 0 else None, None if rc == 0 else f"mqtt_rc_{rc}", command_id),
                )
        return self.command(command_id)

    def command(self, command_id: str) -> dict[str, Any]:
        with self._connect(readonly=True) as conn:
            row = conn.execute("SELECT * FROM smartfarm_commands WHERE command_id=?", (command_id,)).fetchone()
        if not row:
            raise KeyError(command_id)
        result = dict(row)
        result["params"] = _safe_json(result.pop("params_json"), {})
        result["detail"] = _safe_json(result.pop("detail_json"), {})
        for key in ("issued_at", "expires_at", "published_at", "ack_at", "observed_at"):
            result[f"{key}_iso"] = _iso(result[key])
        return result

    def _device_health(self, row: sqlite3.Row, now: float) -> tuple[str, float]:
        age = max(0.0, now - float(row["last_seen_at"]))
        declared = str(row["state"])
        if declared == "offline" or age >= self.offline_after_s:
            return "offline", age
        if declared == "fault":
            return "fault", age
        if age >= self.stale_after_s:
            return "stale", age
        if declared == "online":
            return "online", age
        return "unknown", age

    def overview(self) -> dict[str, Any]:
        now = _now()
        self._expire_commands(now)
        with self._connect(readonly=True) as conn:
            device_rows = conn.execute("SELECT * FROM smartfarm_devices ORDER BY kind,zone_id,device_id").fetchall()
            reading_rows = conn.execute(
                """SELECT r.* FROM smartfarm_readings r
                   JOIN (SELECT zone_id,metric,MAX(ingested_at) latest FROM smartfarm_readings GROUP BY zone_id,metric) x
                   ON r.zone_id=x.zone_id AND r.metric=x.metric AND r.ingested_at=x.latest
                   ORDER BY r.zone_id,r.metric"""
            ).fetchall()
            command_rows = conn.execute(
                "SELECT * FROM smartfarm_commands ORDER BY issued_at DESC LIMIT 30"
            ).fetchall()
            alert_rows = conn.execute(
                "SELECT * FROM smartfarm_alerts WHERE status='open' ORDER BY severity DESC,updated_at DESC LIMIT 50"
            ).fetchall()
            pump_rows = conn.execute("SELECT key,value FROM smartfarm_meta WHERE key LIKE 'pump:%'").fetchall()
        devices = []
        fault_device_ids = {
            str(row["device_id"])
            for row in alert_rows
            if row["severity"] in {"high", "critical"} and row["device_id"]
        }
        for row in device_rows:
            health, age = self._device_health(row, now)
            if row["device_id"] in fault_device_ids:
                health = "fault"
            devices.append(
                {
                    "device_id": row["device_id"],
                    "kind": row["kind"],
                    "zone_id": row["zone_id"],
                    "board": row["board"],
                    "firmware": row["firmware"],
                    "boot_id": row["boot_id"],
                    "ip": row["ip"],
                    "rssi_dbm": row["rssi_dbm"],
                    "uptime_s": row["uptime_s"],
                    "watchdog_max_run_ms": row["watchdog_max_run_ms"],
                    "capabilities": _safe_json(row["capabilities_json"], {}),
                    "health": health,
                    "last_seen_age_s": round(age, 1),
                    "last_seen_at": _iso(row["last_seen_at"]),
                }
            )
        zones: dict[str, dict[str, Any]] = {}
        for row in reading_rows:
            zone = zones.setdefault(row["zone_id"], {"zone_id": row["zone_id"], "metrics": {}, "pump": {"state": "unknown"}})
            zone["metrics"][row["metric"]] = {
                "value": row["value"],
                "quality": row["quality"],
                "recorded_at": _iso(row["ingested_at"]),
                "age_s": round(max(0.0, now - row["ingested_at"]), 1),
            }
        for row in pump_rows:
            zone_id = row["key"].split(":", 1)[1]
            zone = zones.setdefault(zone_id, {"zone_id": zone_id, "metrics": {}, "pump": {"state": "unknown"}})
            pump = _safe_json(row["value"], {"state": "unknown"})
            pump["observed_at"] = _iso(pump.get("observed_at"))
            zone["pump"] = pump
        device_counts = {state: 0 for state in ("online", "stale", "offline", "fault", "unknown")}
        for device in devices:
            device_counts[device["health"]] += 1
        return {
            "generated_at": _iso(now),
            "runtime": {
                "mqtt_configured": self.health.configured,
                "mqtt_connected": self.health.connected,
                "mqtt_host": self.mqtt_host or None,
                "last_connect_at": _iso(self.health.last_connect_at),
                "last_message_at": _iso(self.health.last_message_at),
                "error": self.health.error,
                "db_path": str(self.db_path),
                "db_ok": True,
                "writer_queue_depth": self._write_queue.qsize(),
                "actuation_enabled": os.getenv("HARNESS_SMARTFARM_ACTUATION_ENABLED", "false").lower() in {"1", "true", "yes"},
                "pump_test_enabled": os.getenv("HARNESS_SMARTFARM_PUMP_TEST_ENABLED", "false").lower() in {"1", "true", "yes"},
            },
            "summary": {
                "devices_total": len(devices),
                "devices": device_counts,
                "zones_total": len(zones),
                "alerts_open": len(alert_rows),
            },
            "zones": list(zones.values()),
            "devices": devices,
            "alerts": [dict(row) | {"evidence": _safe_json(row["evidence_json"], {})} for row in alert_rows],
            "commands": [self._command_row(row) for row in command_rows],
        }

    def _command_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "command_id": row["command_id"],
            "device_id": row["device_id"],
            "zone_id": row["zone_id"],
            "kind": row["kind"],
            "actor": row["actor"],
            "status": row["status"],
            "safety_reason": row["safety_reason"],
            "issued_at": _iso(row["issued_at"]),
            "ack_at": _iso(row["ack_at"]),
            "observed_at": _iso(row["observed_at"]),
            "observed_state": row["observed_state"],
        }

    def _expire_commands(self, now: float) -> None:
        with self._db_lock:
            with self._connect() as conn:
                conn.execute(
                    """UPDATE smartfarm_commands SET status='unknown',safety_reason='ack_or_observation_timeout'
                       WHERE expires_at<? AND status IN ('created','published','acknowledged')""",
                    (now,),
                )

    def history(self, zone_id: str, metric: str, since_s: int, limit: int = 600) -> dict[str, Any]:
        if metric not in VALID_METRICS:
            raise ValueError("unsupported metric")
        since = _now() - max(60, min(since_s, 31 * 86400))
        limit = max(10, min(limit, 2000))
        with self._connect(readonly=True) as conn:
            rows = conn.execute(
                """SELECT value,quality,ingested_at FROM smartfarm_readings
                   WHERE zone_id=? AND metric=? AND ingested_at>=?
                   ORDER BY ingested_at DESC LIMIT ?""",
                (zone_id, metric, since, limit),
            ).fetchall()
        points = [
            {"value": row["value"], "quality": row["quality"], "recorded_at": _iso(row["ingested_at"])}
            for row in reversed(rows)
        ]
        return {"zone_id": zone_id, "metric": metric, "points": points, "generated_at": _iso(_now())}

    def pump_safety(
        self, zone_id: str, duration_s: int, *, test_mode: bool = False
    ) -> tuple[bool, str, str | None]:
        feature_flag = (
            "HARNESS_SMARTFARM_PUMP_TEST_ENABLED"
            if test_mode
            else "HARNESS_SMARTFARM_ACTUATION_ENABLED"
        )
        if not os.getenv(feature_flag, "false").lower() in {"1", "true", "yes"}:
            return False, "pump_test_disabled" if test_mode else "actuation_disabled", None
        now = _now()
        with self._connect(readonly=True) as conn:
            rows = conn.execute(
                "SELECT * FROM smartfarm_devices WHERE zone_id=? ORDER BY last_seen_at DESC",
                (zone_id,),
            ).fetchall()
            active = conn.execute(
                """SELECT 1 FROM smartfarm_commands WHERE zone_id=? AND kind IN ('pump_on','pump_test')
                   AND status IN ('created','published','acknowledged','running','observed') LIMIT 1""",
                (zone_id,),
            ).fetchone()
            bad_reading = conn.execute(
                """SELECT quality FROM smartfarm_readings WHERE zone_id=? AND metric IN ('soil_pct','soil_raw')
                   ORDER BY ingested_at DESC LIMIT 1""",
                (zone_id,),
            ).fetchone()
        if active:
            return False, "pump_or_command_already_active", None
        for row in rows:
            health, _ = self._device_health(row, now)
            watchdog_ms = int(row["watchdog_max_run_ms"] or 0)
            if health == "online" and row["boot_id"] and watchdog_ms > duration_s * 1000:
                if bad_reading and bad_reading["quality"] != "good":
                    return False, "sensor_fault", row["device_id"]
                return True, "clear", row["device_id"]
        return False, "no_fresh_watchdog_capable_device", None

    def diagnostic_safety(self, zone_id: str, invasive: bool) -> tuple[bool, str]:
        if not invasive:
            return True, "clear"
        with self._connect(readonly=True) as conn:
            pump = conn.execute("SELECT value FROM smartfarm_meta WHERE key=?", (f"pump:{zone_id}",)).fetchone()
        state = _safe_json(pump["value"], {}).get("state") if pump else "unknown"
        if state != "off":
            return False, "invasive_test_requires_observed_pump_off"
        return True, "clear"

    def purge(self, raw_days: int = 30) -> int:
        cutoff = _now() - max(1, raw_days) * 86400
        with self._db_lock:
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM smartfarm_readings WHERE ingested_at<?", (cutoff,))
                return int(cursor.rowcount)


_RUNTIME: SmartfarmRuntime | None = None
_RUNTIME_LOCK = threading.Lock()


def get_smartfarm_runtime() -> SmartfarmRuntime:
    global _RUNTIME
    if _RUNTIME is not None:
        return _RUNTIME
    with _RUNTIME_LOCK:
        if _RUNTIME is None:
            default_path = Path.home() / ".harness" / "smartfarm-operations.db"
            db_path = Path(os.getenv("HARNESS_SMARTFARM_DB_PATH", str(default_path))).expanduser()
            runtime = SmartfarmRuntime(
                db_path,
                mqtt_host=os.getenv("HARNESS_SMARTFARM_MQTT_HOST", ""),
                mqtt_port=int(os.getenv("HARNESS_SMARTFARM_MQTT_PORT", "1883")),
            )
            runtime.start()
            _RUNTIME = runtime
    return _RUNTIME
