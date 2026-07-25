"""Smartfarm 라즈베리파이 허브 - 1구역 프로토타입.

역할: 구역별 ESP32 노드가 publish하는 센서값을 구독해 SQLite에 적재하고,
      토양수분 임계값 기반으로 급수 시작/중단 명령을 다시 MQTT로 publish한다.

구역을 늘릴 때 이 파일은 수정하지 않는다. config.yaml의 zones 항목만 추가하면
새 구역의 토픽(farm/<zone_id>/...)이 자동으로 구독/제어된다.

임계값(soil_min_pct/soil_target_pct 등)은 고정값이 아니다. config.yaml을 CONFIG_RELOAD_INTERVAL_S
주기로 다시 읽어 반영하므로, scripts/smartfarm_ops.py의 threshold-propose(데이터 기반 제안)
-> threshold-decide(CEO 승인) -> threshold-apply(config.yaml 패치)를 거친 값이 이 허브 재시작
없이도 자동 반영된다. 이 파일은 여전히 펌프를 켜고 끄는 유일한 주체다 — OpenClaw/LLM은
config.yaml 파일 내용만 바꿀 뿐, MQTT 명령을 직접 보내지 않는다.

실행: python hub.py --config config.yaml
"""
from __future__ import annotations

import argparse
import sqlite3
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import yaml

HERE = Path(__file__).parent
CONFIG_RELOAD_INTERVAL_S = 30


def _invalid_zone_cfg_reason(zone_id: str, cfg: dict) -> str | None:
    """Sanity-check a zone's threshold values before they're allowed to replace
    the live ones. Guards against a bad manual edit or a bug upstream silently
    turning the pump into an always-on/always-off state."""
    required = ("soil_min_pct", "soil_target_pct", "water_duration_s", "cooldown_s")
    missing = [k for k in required if k not in cfg]
    if missing:
        return f"missing key(s): {missing}"
    if not (0 <= cfg["soil_min_pct"] < cfg["soil_target_pct"] <= 100):
        return (
            f"soil_min_pct={cfg['soil_min_pct']} must be < soil_target_pct="
            f"{cfg['soil_target_pct']}, both within [0, 100]"
        )
    if cfg["water_duration_s"] <= 0 or cfg["cooldown_s"] < 0:
        return "water_duration_s must be > 0 and cooldown_s must be >= 0"
    return None


class ZoneState:
    def __init__(self, zone_id: str, cfg: dict):
        self.zone_id = zone_id
        self.cfg = cfg
        self.pump_on = False
        self.last_off_time = 0.0
        self.off_timer: threading.Timer | None = None
        self.lock = threading.Lock()


class SmartfarmHub:
    def __init__(self, config: dict, config_path: Path):
        self.config = config
        self.config_path = config_path
        self._config_mtime = config_path.stat().st_mtime
        self.db_path = HERE / config["db_path"]
        self.zones = {
            zone_id: ZoneState(zone_id, zone_cfg)
            for zone_id, zone_cfg in config["zones"].items()
        }
        self._init_db()

        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.executescript((HERE / "schema.sql").read_text())
        conn.commit()
        conn.close()

    def _db(self):
        return sqlite3.connect(self.db_path)

    def _on_connect(self, client, userdata, flags, rc):
        client.subscribe("farm/+/soil")
        client.subscribe("farm/+/temp")
        client.subscribe("farm/+/humidity")
        client.subscribe("farm/+/pump/status")

    def _on_message(self, client, userdata, msg):
        parts = msg.topic.split("/")
        if len(parts) < 3 or parts[0] != "farm":
            return
        zone_id = parts[1]
        if zone_id not in self.zones:
            return  # config.yaml에 등록되지 않은 구역은 무시

        payload = msg.payload.decode(errors="ignore").strip()

        if parts[2] == "soil":
            self._log_reading(zone_id, "soil_pct", payload)
            self._evaluate_irrigation(zone_id, payload)
        elif parts[2] == "temp":
            self._log_reading(zone_id, "temp_c", payload)
        elif parts[2] == "humidity":
            self._log_reading(zone_id, "humidity_pct", payload)
        elif parts[2] == "pump" and len(parts) > 3 and parts[3] == "status":
            pass  # 노드 측 실제 상태 확인용 echo. 별도 처리 불필요 (허브가 상태 소유)

    def _log_reading(self, zone_id: str, metric: str, raw_value: str):
        try:
            value = float(raw_value)
        except ValueError:
            return
        conn = self._db()
        conn.execute(
            "INSERT INTO sensor_readings (zone_id, metric, value) VALUES (?, ?, ?)",
            (zone_id, metric, value),
        )
        conn.commit()
        conn.close()

    def _log_pump_event(self, zone_id: str, action: str, reason: str, soil_pct: float | None):
        conn = self._db()
        conn.execute(
            "INSERT INTO pump_events (zone_id, action, reason, soil_pct_at_event) VALUES (?, ?, ?, ?)",
            (zone_id, action, reason, soil_pct),
        )
        conn.commit()
        conn.close()

    def _evaluate_irrigation(self, zone_id: str, raw_soil: str):
        try:
            soil_pct = float(raw_soil)
        except ValueError:
            return

        zone = self.zones[zone_id]
        cfg = zone.cfg

        with zone.lock:
            if not zone.pump_on:
                cooldown_ok = (time.time() - zone.last_off_time) > cfg["cooldown_s"]
                if soil_pct < cfg["soil_min_pct"] and cooldown_ok:
                    self._start_pump(zone, soil_pct, reason="threshold")
            else:
                if soil_pct >= cfg["soil_target_pct"]:
                    self._stop_pump(zone, soil_pct, reason="target_reached")

    def _start_pump(self, zone: ZoneState, soil_pct: float, reason: str):
        zone.pump_on = True
        self.client.publish(f"farm/{zone.zone_id}/pump/cmd", "on")
        self._log_pump_event(zone.zone_id, "on", reason, soil_pct)

        duration = zone.cfg["water_duration_s"]
        zone.off_timer = threading.Timer(
            duration, self._timeout_stop_pump, args=(zone,)
        )
        zone.off_timer.daemon = True
        zone.off_timer.start()

    def _stop_pump(self, zone: ZoneState, soil_pct: float | None, reason: str):
        if zone.off_timer is not None:
            zone.off_timer.cancel()
            zone.off_timer = None
        zone.pump_on = False
        zone.last_off_time = time.time()
        self.client.publish(f"farm/{zone.zone_id}/pump/cmd", "off")
        self._log_pump_event(zone.zone_id, "off", reason, soil_pct)

    def _timeout_stop_pump(self, zone: ZoneState):
        with zone.lock:
            if zone.pump_on:
                self._stop_pump(zone, soil_pct=None, reason="timeout")

    def _reload_config_if_changed(self):
        """Pick up config.yaml edits (manual, or via scripts/smartfarm_ops.py's
        approved threshold-apply) without restarting the process. Only known
        zones' threshold dicts are replaced; a newly-appeared zone_id is added
        so it starts being controlled without a restart too. Invalid values
        are rejected and the previous thresholds keep running."""
        try:
            mtime = self.config_path.stat().st_mtime
        except OSError:
            return
        if mtime == self._config_mtime:
            return
        self._config_mtime = mtime

        try:
            new_config = yaml.safe_load(self.config_path.read_text())
        except Exception as exc:  # noqa: BLE001 - malformed file must not crash the hub
            print(f"[reload] failed to parse {self.config_path}: {exc}; keeping previous thresholds")
            return

        for zone_id, new_cfg in (new_config.get("zones") or {}).items():
            reason = _invalid_zone_cfg_reason(zone_id, new_cfg)
            if reason:
                print(f"[reload] rejected zone '{zone_id}' update ({reason}); keeping previous thresholds")
                continue
            if zone_id in self.zones:
                zone = self.zones[zone_id]
                if zone.cfg != new_cfg:
                    print(f"[reload] zone '{zone_id}' thresholds updated: {zone.cfg} -> {new_cfg}")
                zone.cfg = new_cfg
            else:
                print(f"[reload] new zone '{zone_id}' detected in config.yaml, adding")
                self.zones[zone_id] = ZoneState(zone_id, new_cfg)

    def run(self):
        self.client.connect(self.config["mqtt"]["host"], self.config["mqtt"]["port"])
        self.client.loop_start()
        try:
            while True:
                time.sleep(CONFIG_RELOAD_INTERVAL_S)
                self._reload_config_if_changed()
        finally:
            self.client.loop_stop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE / "config.yaml"))
    args = parser.parse_args()

    config_path = Path(args.config)
    config = yaml.safe_load(config_path.read_text())
    SmartfarmHub(config, config_path).run()


if __name__ == "__main__":
    main()
