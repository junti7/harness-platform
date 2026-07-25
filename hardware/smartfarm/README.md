# Smartfarm 프로토타입

ESP32/ESP8266 센서 노드 + 라즈베리파이 허브(MQTT) 구조. 스케치(`soil_node.ino`)는 두 칩 공용이며
WiFi 라이브러리만 전처리기로 분기한다. 구역을 늘릴 때 허브 코드는 그대로 두고
`pi_hub/config.yaml`에 구역을 추가하고 노드를 새 `config.h`로 재플래싱만 하면 된다.

## 구성

```
soil_node/   ESP32/ESP8266 공용 아두이노 스케치 (토양수분+DHT22 읽기, 릴레이로 펌프 제어)
  soil_node.ino               보드 공용 로직
  config.example.esp32.h      ESP32용 설정 템플릿 (12비트 ADC, GPIO34 등)
  config.example.esp8266.h    ESP8266용 설정 템플릿 (10비트 ADC, A0 아날로그 전용)
pi_hub/      라즈베리파이 MQTT 허브 (Mosquitto 구독, SQLite 로깅, 급수 판단)
```

## 1. 라즈베리파이 준비

```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto

cd hardware/smartfarm/pi_hub
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp config.example.yaml config.yaml   # 값 채우기 (mqtt host는 보통 localhost)
python hub.py --config config.yaml
```

## 2. 센서 노드 준비 (ESP32 / ESP8266)

1. 보드 core + 라이브러리 설치 (arduino-cli 기준).
   ```bash
   # ESP32
   arduino-cli config add board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   arduino-cli core install esp32:esp32

   # ESP8266
   arduino-cli config add board_manager.additional_urls https://arduino.esp8266.com/stable/package_esp8266com_index.json
   arduino-cli core install esp8266:esp8266

   arduino-cli lib install "PubSubClient" "DHT sensor library" "Adafruit Unified Sensor"
   ```
2. 보드에 맞는 템플릿을 `soil_node/config.h`로 복사 후 WiFi/브로커 IP/캘리브레이션 값 채우기.
   - ESP32 → `config.example.esp32.h`
   - ESP8266 → `config.example.esp8266.h`
3. 배선.
   - **ESP32**: 토양수분 센서 AOUT → GPIO34, DHT22 → GPIO4, 릴레이 IN → GPIO26
   - **ESP8266**: 토양수분 센서 AOUT → A0(유일한 아날로그 핀), DHT22 → GPIO4(D2), 릴레이 IN → GPIO5(D1)
   - (config.h에서 pin 변경 가능. ESP8266은 아날로그 입력이 A0 하나뿐이라 SOIL_MOISTURE_PIN은 항상 A0.)
4. 컴파일/업로드 (FQBN은 실제 보드에 맞게, 예: `esp32:esp32:esp32` / `esp8266:esp8266:nodemcuv2`).
   ```bash
   arduino-cli compile --fqbn <FQBN> hardware/smartfarm/soil_node
   arduino-cli upload -p <포트> --fqbn <FQBN> hardware/smartfarm/soil_node
   ```
5. 업로드 후 시리얼 모니터(115200 baud)로 WiFi/MQTT 연결 확인.

## 3. 동작 확인

```bash
mosquitto_sub -h <파이IP> -t 'farm/#' -v
```

토양수분/온습도 값이 주기적으로 올라오고, `soil_pct`가 `soil_min_pct` 밑으로 내려가면
허브가 `farm/zone1/pump/cmd`에 `on`을 publish하는지 확인한다.

## 4. 안전장치 (중요)

- **노드 로컬**: `PUMP_MAX_RUN_MS` (config.h) — 허브와 통신이 끊겨도 이 시간이 지나면 노드가 스스로 펌프를 끈다.
- **허브**: `water_duration_s` (config.yaml) — 노드측 최대값보다 짧게 설정해서 정상 상황에서는 허브가 먼저 끈다.
- 두 안전장치 다 값이 겹치지 않게 반드시 `water_duration_s < PUMP_MAX_RUN_MS`로 유지한다.
- **급수 임계값(`soil_min_pct`/`soil_target_pct`)은 고정값이 아니다.** `hub.py`는 `CONFIG_RELOAD_INTERVAL_S`(기본 30초)마다
  `config.yaml`을 다시 읽어 반영하므로, 아래 6번의 `threshold-apply`로 승인된 변경이 허브 재시작 없이 자동 적용된다.
  펌프를 켜고 끄는 결정은 여전히 `hub.py` 단독 소유이며, 새 값은 `0 ≤ soil_min_pct < soil_target_pct ≤ 100` 및
  `water_duration_s > 0`, `cooldown_s ≥ 0`을 만족하지 못하면 리로드 시점에 거부되고 이전 값이 유지된다
  (거부/적용 로그는 `journalctl -u harness-smartfarm-hub`에서 확인).

## 5. 구역 추가 절차

구역마다 ESP32/ESP8266을 섞어 써도 무방하다 (허브는 칩 종류를 모르고 MQTT 토픽만 본다).

1. `pi_hub/config.yaml`의 `zones`에 `zone2` 항목 추가 (임계값은 zone1과 다르게 설정 가능).
2. 새 노드에 맞는 템플릿(`config.example.esp32.h` 또는 `config.example.esp8266.h`)을 zone2용 `config.h`로 복사 (`ZONE_ID`, `MQTT_CLIENT_ID`만 변경, 캘리브레이션 값은 보드/센서별로 실측).
3. 새 노드에 재플래싱, 배선.
4. 허브 재시작 없이도 `farm/zone2/...` 토픽이 자동 구독됨 (와일드카드 구독이라 코드 변경 불필요).

## 6. OpenClaw 연동 (읽기 전용 분석 + 제안, 액추에이터 제어 없음)

`scripts/openclaw_smartfarm_research_bridge.py`가 부품 조달 리서치에 더해 운영 커맨드를 제공한다.
어떤 커맨드도 MQTT 명령을 보내거나 액추에이터를 직접 건드리지 않는다 — 펌프 제어는 여전히
`pi_hub/hub.py`의 결정론적 로직 단독 소유다.

```bash
# 이상탐지 (센서 무응답/고정값/범위이탈, 펌프 단주기 작동)
python scripts/openclaw_smartfarm_research_bridge.py alerts --db pi_hub/smartfarm.db --config pi_hub/config.yaml

# 존별 상태 리포트 (일간/주간)
python scripts/openclaw_smartfarm_research_bridge.py report --db pi_hub/smartfarm.db --config pi_hub/config.yaml --period-hours 24

# 데이터 기반 임계값 조정 제안 (제안만, 자동 반영 없음)
python scripts/openclaw_smartfarm_research_bridge.py threshold-propose --db pi_hub/smartfarm.db --config pi_hub/config.yaml

# CEO 승인/반려 기록 (threshold-propose 결과의 proposal_id 사용)
python scripts/openclaw_smartfarm_research_bridge.py threshold-decide <proposal_id> approved --note "..."

# 승인된 건만 config.yaml에 반영 (승인 기록 없으면 거부, 코멘트는 그대로 보존)
python scripts/openclaw_smartfarm_research_bridge.py threshold-apply <proposal_id>
```

`alerts`/`report`는 `--deliver <route>`로 기존 Slack 라우트에 요약을 보낼 수 있다 (예:
`--deliver ops_incidents`). 다만 이 라우트들은 실제 회사 공용 채널이라, 스마트팜 알림을
바로 흘려보낼지는 채널을 지정하기 전에 판단이 필요하다 — 지정 안 하면 JSON 출력만 하고 아무것도
발송하지 않는다.

`threshold-apply`는 직전에 `threshold-decide`로 기록된 결정이 `approved`인 경우에만 동작하며,
`config.yaml`의 다른 라인/한글 주석은 건드리지 않고 해당 수치만 치환한다. 적용된 값은 `hub.py`가
`CONFIG_RELOAD_INTERVAL_S` 주기로 스스로 다시 읽어가므로 허브를 재시작할 필요가 없다 (4번 참고).
