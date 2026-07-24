# Smartfarm 1구역 프로토타입

ESP32 센서 노드 + 라즈베리파이 허브(MQTT) 구조. 구역을 늘릴 때 허브 코드는 그대로 두고
`pi_hub/config.yaml`에 구역을 추가하고 ESP32를 새 `config.h`로 재플래싱만 하면 된다.

## 구성

```
esp32/soil_node/   ESP32 아두이노 스케치 (토양수분+DHT22 읽기, 릴레이로 펌프 제어)
pi_hub/            라즈베리파이 MQTT 허브 (Mosquitto 구독, SQLite 로깅, 급수 판단)
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

## 2. ESP32 준비

1. Arduino IDE에 ESP32 보드 패키지, `PubSubClient`, `DHT sensor library`(Adafruit) 설치.
2. `esp32/soil_node/config.example.h`를 같은 폴더의 `config.h`로 복사 후 WiFi/브로커 IP/캘리브레이션 값 채우기.
3. 배선: 토양수분 센서 AOUT → GPIO34, DHT22 → GPIO4, 릴레이 IN → GPIO26 (config.h에서 pin 변경 가능).
4. 업로드 후 시리얼 모니터로 WiFi/MQTT 연결 확인.

## 3. 동작 확인

```bash
mosquitto_sub -h <파이IP> -t 'farm/#' -v
```

토양수분/온습도 값이 주기적으로 올라오고, `soil_pct`가 `soil_min_pct` 밑으로 내려가면
허브가 `farm/zone1/pump/cmd`에 `on`을 publish하는지 확인한다.

## 4. 안전장치 (중요)

- **ESP32 로컬**: `PUMP_MAX_RUN_MS` (config.h) — 허브와 통신이 끊겨도 이 시간이 지나면 노드가 스스로 펌프를 끈다.
- **허브**: `water_duration_s` (config.yaml) — ESP32측 최대값보다 짧게 설정해서 정상 상황에서는 허브가 먼저 끈다.
- 두 안전장치 다 값이 겹치지 않게 반드시 `water_duration_s < PUMP_MAX_RUN_MS`로 유지한다.

## 5. 구역 추가 절차

1. `pi_hub/config.yaml`의 `zones`에 `zone2` 항목 추가 (임계값은 zone1과 다르게 설정 가능).
2. `esp32/soil_node/config.h`를 zone2용으로 복사 (`ZONE_ID`, `MQTT_CLIENT_ID`만 변경).
3. 새 ESP32에 재플래싱, 배선.
4. 허브 재시작 없이도 `farm/zone2/...` 토픽이 자동 구독됨 (와일드카드 구독이라 코드 변경 불필요).
