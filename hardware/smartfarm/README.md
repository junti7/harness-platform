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

## 5. 구역 추가 절차

구역마다 ESP32/ESP8266을 섞어 써도 무방하다 (허브는 칩 종류를 모르고 MQTT 토픽만 본다).

1. `pi_hub/config.yaml`의 `zones`에 `zone2` 항목 추가 (임계값은 zone1과 다르게 설정 가능).
2. 새 노드에 맞는 템플릿(`config.example.esp32.h` 또는 `config.example.esp8266.h`)을 zone2용 `config.h`로 복사 (`ZONE_ID`, `MQTT_CLIENT_ID`만 변경, 캘리브레이션 값은 보드/센서별로 실측).
3. 새 노드에 재플래싱, 배선.
4. 허브 재시작 없이도 `farm/zone2/...` 토픽이 자동 구독됨 (와일드카드 구독이라 코드 변경 불필요).
