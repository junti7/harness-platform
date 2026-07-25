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
import json
import os
import platform
import sqlite3
import socket
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt
import yaml

HERE = Path(__file__).parent
CONFIG_RELOAD_INTERVAL_S = 30

# soil_raw가 이보다 오래됐으면 없는 것으로 본다. 노드는 SENSOR_READ_INTERVAL_MS(30초)마다
# 발행하므로 3주기를 못 채우면 raw 경로가 끊긴 것이다.
SOIL_RAW_MAX_AGE_S = 90


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

    has_min = "soil_raw_min" in cfg
    has_max = "soil_raw_max" in cfg
    if has_min != has_max:
        return "soil_raw_min and soil_raw_max must be set together (or both omitted)"
    if has_min and not (cfg["soil_raw_min"] < cfg["soil_raw_max"]):
        return (
            f"soil_raw_min={cfg['soil_raw_min']} must be < soil_raw_max={cfg['soil_raw_max']}"
        )

    follows = cfg.get("follows_pump")
    if follows is not None:
        if not isinstance(follows, str):
            return "follows_pump must be a zone id string"
        if follows == zone_id:
            return "follows_pump cannot point at its own zone"
    return None


def _invalid_follow_graph_reason(zones: dict) -> str | None:
    """follows_pump 참조가 전체적으로 성립하는지 본다. 개별 구역만 봐서는
    존재하지 않는 구역을 가리키거나 사슬이 생기는 걸 알 수 없다."""
    for zone_id, cfg in zones.items():
        target = cfg.get("follows_pump")
        if target is None:
            continue
        if target not in zones:
            return f"'{zone_id}'의 follows_pump='{target}'는 존재하지 않는 구역이다"
        # 사슬(A->B->C)은 허용하지 않는다. 정지 전파 순서와 락 순서가 복잡해지고,
        # 실무상 필요한 건 '한 센서가 여러 밸브를 연다'는 1단 구조뿐이다.
        if zones[target].get("follows_pump") is not None:
            return (
                f"'{zone_id}'가 따라가는 '{target}'도 다른 구역을 따라간다 "
                "(follows_pump 사슬은 허용하지 않음)"
            )
    return None


class ZoneState:
    def __init__(self, zone_id: str, cfg: dict):
        self.zone_id = zone_id
        self.cfg = cfg
        self.pump_on = False
        self.last_off_time = 0.0
        self.off_timer: threading.Timer | None = None
        self.lock = threading.Lock()
        # 같은 측정 주기의 raw ADC 값. 노드가 soil보다 먼저 발행하므로 soil 처리 시점에
        # 채워져 있다. 고장 판정에 쓰이며, 없거나 낡으면 급수를 막는다.
        self.last_soil_raw: float | None = None
        self.last_soil_raw_time = 0.0
        self.fault_logged = False  # 같은 고장으로 로그를 도배하지 않기 위한 플래그


class SmartfarmHub:
    def __init__(self, config: dict, config_path: Path):
        self.config = config
        self.config_path = config_path
        self._config_mtime = config_path.stat().st_mtime
        self.db_path = HERE / config["db_path"]
        graph_reason = _invalid_follow_graph_reason(config["zones"])
        if graph_reason:
            raise ValueError(f"config.yaml follows_pump 설정 오류: {graph_reason}")
        self.zones = {
            zone_id: ZoneState(zone_id, zone_cfg)
            for zone_id, zone_cfg in config["zones"].items()
        }
        self.last_manual_sequence = {zone_id: 0 for zone_id in self.zones}
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
        client.subscribe("farm/+/soil_raw")
        client.subscribe("farm/+/temp")
        client.subscribe("farm/+/humidity")
        client.subscribe("farm/+/pump/status")
        client.subscribe("farm/+/command/request")
        self._publish_hub_status("online")

    def _publish_hub_status(self, state: str):
        payload = {
            "device_id": os.getenv("SMARTFARM_HUB_DEVICE_ID", "pi-hub"),
            "kind": "raspberry_pi",
            "board": platform.machine(),
            "firmware": "smartfarm-pi-hub-2.0",
            "boot_id": self._boot_id,
            "host": socket.gethostname(),
            "ip": socket.gethostbyname(socket.gethostname()),
            "uptime_s": int(time.monotonic()),
            "db_ok": self.db_path.exists(),
            "config_ok": True,
            "zones": sorted(self.zones),
            "state": state,
            "ts": time.time(),
        }
        self.client.publish(
            "farm/system/pi-hub/status",
            json.dumps(payload, separators=(",", ":")),
            qos=1,
            retain=True,
        )

    def _on_message(self, client, userdata, msg):
        parts = msg.topic.split("/")
        if len(parts) < 3 or parts[0] != "farm":
            return
        zone_id = parts[1]
        if zone_id not in self.zones:
            return  # config.yaml에 등록되지 않은 구역은 무시

        payload = msg.payload.decode(errors="ignore").strip()

        if parts[2] == "command" and len(parts) > 3 and parts[3] == "request":
            self._handle_manual_command(zone_id, payload)
        elif parts[2] == "soil":
            self._log_reading(zone_id, "soil_pct", payload)
            self._evaluate_irrigation(zone_id, payload)
        elif parts[2] == "soil_raw":
            self._record_soil_raw(zone_id, payload)
        elif parts[2] == "temp":
            self._log_reading(zone_id, "temp_c", payload)
        elif parts[2] == "humidity":
            self._log_reading(zone_id, "humidity_pct", payload)
        elif parts[2] == "pump" and len(parts) > 3 and parts[3] == "status":
            # 실제 edge echo가 최종 관측 상태다. hub가 재시작했거나 watchdog가
            # 독립적으로 OFF한 경우에도 in-memory state를 현실과 다시 맞춘다.
            state = payload.lower()
            if state in {"on", "off"}:
                zone = self.zones[zone_id]
                with zone.lock:
                    observed_on = state == "on"
                    if zone.pump_on and not observed_on:
                        if zone.off_timer is not None:
                            zone.off_timer.cancel()
                            zone.off_timer = None
                        zone.last_off_time = time.time()
                    zone.pump_on = observed_on

    def _publish_command_ack(
        self, zone_id: str, command_id: str, accepted: bool, phase: str, reason: str
    ):
        if not command_id:
            return
        payload = {
            "command_id": command_id,
            "accepted": accepted,
            "phase": phase,
            "reason": reason,
            "ts": time.time(),
        }
        self.client.publish(
            f"farm/{zone_id}/command/ack",
            json.dumps(payload, separators=(",", ":")),
            qos=1,
            retain=False,
        )

    def _handle_manual_command(self, zone_id: str, payload: str):
        """Manual control still flows through the deterministic Pi owner.

        Harness OS never talks around the hub to the relay. The hub rejects
        retained/replayed/expired intent, updates its ZoneState, and only then
        emits the legacy edge command understood by deployed firmware.
        """
        try:
            command = json.loads(payload)
        except (TypeError, ValueError):
            return
        if not isinstance(command, dict):
            return
        command_id = str(command.get("command_id") or "")
        kind = str(command.get("kind") or "")
        try:
            sequence = int(command.get("sequence") or 0)
            expires_at = float(command.get("expires_at") or 0)
        except (TypeError, ValueError):
            self._publish_command_ack(zone_id, command_id, False, "rejected", "invalid_sequence_or_expiry")
            return
        if sequence <= self.last_manual_sequence.get(zone_id, 0):
            self._publish_command_ack(zone_id, command_id, False, "rejected", "stale_sequence")
            return
        if expires_at <= time.time():
            self._publish_command_ack(zone_id, command_id, False, "rejected", "expired")
            return
        if kind not in {"pump_on", "pump_off"}:
            return  # diagnostics are owned directly by the edge node

        zone = self.zones[zone_id]
        params = command.get("params") if isinstance(command.get("params"), dict) else {}
        try:
            duration_s = int(params.get("duration_s") or 0)
        except (TypeError, ValueError):
            duration_s = 0
        with zone.lock:
            self.last_manual_sequence[zone_id] = sequence
            if kind == "pump_off":
                if zone.pump_on:
                    self._stop_pump(zone, soil_pct=None, reason="manual_dashboard")
                else:
                    # Always send OFF even if hub already believes it is off.
                    self.client.publish(f"farm/{zone_id}/pump/cmd", "off", qos=1, retain=False)
                self._publish_command_ack(zone_id, command_id, True, "acknowledged", "off_dispatched")
                return

            if duration_s <= 0 or duration_s > int(zone.cfg["water_duration_s"]):
                self._publish_command_ack(
                    zone_id, command_id, False, "rejected", "duration_exceeds_hub_limit"
                )
                return
            fault = self._soil_fault_reason(zone)
            if fault is not None:
                self._publish_command_ack(zone_id, command_id, False, "rejected", "sensor_fault")
                return
            cooldown_ok = (time.time() - zone.last_off_time) > zone.cfg["cooldown_s"]
            if zone.pump_on or not cooldown_ok:
                self._publish_command_ack(zone_id, command_id, False, "rejected", "active_or_cooldown")
                return
            self._start_pump(zone, soil_pct=None, reason="manual_dashboard", duration_s=duration_s)
            self._publish_command_ack(zone_id, command_id, True, "acknowledged", "on_dispatched")

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

    def _record_soil_raw(self, zone_id: str, payload: str):
        try:
            value = float(payload)
        except ValueError:
            return
        zone = self.zones[zone_id]
        zone.last_soil_raw = value
        zone.last_soil_raw_time = time.time()
        self._log_reading(zone_id, "soil_raw", payload)

    def _soil_fault_reason(self, zone: ZoneState) -> str | None:
        """4-20mA 전류루프의 live zero를 소프트웨어로 흉내낸다.

        퍼센트 값만으로는 고장을 알 수 없다. 노드가 map()+constrain()으로 눌러버리기
        때문에, 배선이 끊긴 floating 핀도 '0%'(바싹 마름)라는 그럴듯한 값이 된다.
        2026-07-25 zone1에서 이 때문에 실제로 유령 급수가 발생했다. 그래서 판정은
        가공 전 raw ADC 값으로 한다 — 정상 센서라면 절대 나올 수 없는 raw는 곧 고장이다.

        soil_raw_min/max가 설정되지 않은 구역은 검증하지 않는다(구버전 펌웨어 호환).
        """
        cfg = zone.cfg
        if "soil_raw_min" not in cfg:
            return None  # 이 구역은 raw 검증을 켜지 않았다

        if zone.last_soil_raw is None:
            return "soil_raw를 한 번도 받지 못했다 (노드 펌웨어가 구버전일 수 있음)"
        age = time.time() - zone.last_soil_raw_time
        if age > SOIL_RAW_MAX_AGE_S:
            return f"soil_raw가 {age:.0f}초 전 값이라 신뢰할 수 없다"
        if not (cfg["soil_raw_min"] <= zone.last_soil_raw <= cfg["soil_raw_max"]):
            return (
                f"soil_raw={zone.last_soil_raw:.0f}이 정상 범위"
                f"[{cfg['soil_raw_min']}, {cfg['soil_raw_max']}] 밖 — 센서 단선/고장 의심"
            )
        return None

    def _evaluate_irrigation(self, zone_id: str, raw_soil: str):
        try:
            soil_pct = float(raw_soil)
        except ValueError:
            return

        zone = self.zones[zone_id]
        cfg = zone.cfg

        # 다른 구역을 따라가는 구역은 스스로 판단하지 않는다. 자체 판단과 미러링이
        # 겹치면 서로 껐다 켰다 하며 상태가 어긋난다. 센서값은 계속 적재되므로
        # 나중에 follows_pump를 떼면 그대로 독립 판단으로 돌아간다.
        if cfg.get("follows_pump") is not None:
            return

        with zone.lock:
            fault = self._soil_fault_reason(zone)
            if fault is not None:
                # 고장이 의심되면 급수하지 않는다. 물을 안 주는 쪽이 안전한 실패 방향이다.
                # 이미 켜져 있었다면 즉시 끈다 — 켜진 근거 자체를 믿을 수 없기 때문이다.
                if zone.pump_on:
                    print(f"[fault] {zone_id}: {fault} -> 급수 중단")
                    self._stop_pump(zone, soil_pct=None, reason="sensor_fault")
                elif not zone.fault_logged:
                    print(f"[fault] {zone_id}: {fault} -> 급수 보류")
                zone.fault_logged = True
                return

            if zone.fault_logged:
                # last_soil_raw는 None일 수 있다: 고장 상태에서 soil_raw_min/max 설정이
                # 제거되면 검증이 꺼지면서 raw 없이 이 경로로 들어온다.
                raw_note = (
                    f"soil_raw={zone.last_soil_raw:.0f}"
                    if zone.last_soil_raw is not None
                    else "raw 검증 비활성화됨"
                )
                print(f"[fault] {zone_id}: 센서 정상 복귀 ({raw_note})")
                zone.fault_logged = False

            if not zone.pump_on:
                cooldown_ok = (time.time() - zone.last_off_time) > cfg["cooldown_s"]
                if soil_pct < cfg["soil_min_pct"] and cooldown_ok:
                    self._start_pump(zone, soil_pct, reason="threshold")
            else:
                if soil_pct >= cfg["soil_target_pct"]:
                    self._stop_pump(zone, soil_pct, reason="target_reached")

    def _followers_of(self, zone_id: str) -> list[ZoneState]:
        return [z for z in self.zones.values() if z.cfg.get("follows_pump") == zone_id]

    def _start_pump(
        self,
        zone: ZoneState,
        soil_pct: float | None,
        reason: str,
        duration_s: int | None = None,
    ):
        zone.pump_on = True
        self.client.publish(f"farm/{zone.zone_id}/pump/cmd", "on", qos=1, retain=False)
        self._log_pump_event(zone.zone_id, "on", reason, soil_pct)

        duration = duration_s if duration_s is not None else zone.cfg["water_duration_s"]
        zone.off_timer = threading.Timer(
            duration, self._timeout_stop_pump, args=(zone,)
        )
        zone.off_timer.daemon = True
        zone.off_timer.start()

        # 이 구역을 따라가는 밸브들도 같이 연다. 따라가는 구역은 스스로 판단하지 않으므로
        # (_evaluate_irrigation에서 조기 반환) 여기서만 켜진다. 각자 자기 water_duration_s로
        # 타이머를 걸어두므로, 선행 구역의 정지 전파가 실패해도 혼자 무한정 열려 있지 않는다.
        # 사슬은 설정 단계에서 막으므로 이 재귀는 1단에서 끝난다.
        for follower in self._followers_of(zone.zone_id):
            with follower.lock:
                if not follower.pump_on:
                    self._start_pump(follower, soil_pct, reason=f"follows:{zone.zone_id}")

    def _stop_pump(self, zone: ZoneState, soil_pct: float | None, reason: str):
        if zone.off_timer is not None:
            zone.off_timer.cancel()
            zone.off_timer = None
        zone.pump_on = False
        zone.last_off_time = time.time()
        self.client.publish(f"farm/{zone.zone_id}/pump/cmd", "off", qos=1, retain=False)
        self._log_pump_event(zone.zone_id, "off", reason, soil_pct)

        for follower in self._followers_of(zone.zone_id):
            with follower.lock:
                if follower.pump_on:
                    self._stop_pump(follower, soil_pct, reason=f"follows:{zone.zone_id}")

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

        new_zones = new_config.get("zones") or {}
        graph_reason = _invalid_follow_graph_reason(new_zones)
        if graph_reason:
            print(f"[reload] rejected: {graph_reason}; keeping previous config")
            return

        for zone_id, new_cfg in new_zones.items():
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
        self._boot_id = f"{socket.gethostname()}-{int(time.time())}"
        offline_payload = json.dumps(
            {
                "device_id": os.getenv("SMARTFARM_HUB_DEVICE_ID", "pi-hub"),
                "kind": "raspberry_pi",
                "state": "offline",
                "boot_id": self._boot_id,
                "ts": time.time(),
            },
            separators=(",", ":"),
        )
        self.client.will_set("farm/system/pi-hub/status", offline_payload, qos=1, retain=True)
        self.client.connect(self.config["mqtt"]["host"], self.config["mqtt"]["port"])
        self.client.loop_start()
        try:
            while True:
                time.sleep(CONFIG_RELOAD_INTERVAL_S)
                self._reload_config_if_changed()
                self._publish_hub_status("online")
        finally:
            if self.client.is_connected():
                self._publish_hub_status("offline")
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
