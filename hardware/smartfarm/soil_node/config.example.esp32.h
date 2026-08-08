// ESP32 노드 설정 템플릿 (12비트 ADC, 0~4095 raw 범위).
// 이 파일을 config.h로 복사한 뒤 실제 값을 채운다. config.h는 git에 커밋하지 않는다.
#pragma once

#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

#define MQTT_BROKER_HOST "192.168.1.x"   // 라즈베리파이 IP (Mosquitto 구동 위치)
#define MQTT_BROKER_PORT 1883
#define MQTT_CLIENT_ID "smartfarm-zone1"

// 구역을 늘릴 때는 노드마다 이 값만 바꿔서 새 config.h로 플래싱한다.
#define ZONE_ID "zone1"

#define SOIL_MOISTURE_PIN 34   // ADC pin
#define DHT_PIN 4
#define PUMP_RELAY_PIN 26

// 토양수분 센서를 아직 배선하지 않았다면 반드시 0으로 둔다.
// 미배선 ADC 핀은 floating이라 노이즈를 읽고, 그 값이 soil로 발행되면 허브가
// 진짜 건조 신호로 믿고 급수를 트리거한다 (2026-07-25 zone1에서 실제 발생).
#define SOIL_SENSOR_ENABLED 1

// 토양 수분 ADC 원시값 캘리브레이션 (센서/토양마다 실측 후 조정)
#define SOIL_DRY_RAW 3000       // 완전 건조 상태 raw 값
#define SOIL_WET_RAW 1200       // 물에 담갔을 때 raw 값

// 로컬 안전장치 — 허브(MQTT)가 응답 없어도 노드 단독으로 지킨다.
#define PUMP_MAX_RUN_MS 15000UL       // 한 번 켜지면 최대 15초 후 강제 OFF
#define SENSOR_READ_INTERVAL_MS 30000UL

// ── I2C 센서 확장 (선택) ─────────────────────────────────────────────────────
// 아래를 하나도 켜지 않으면 노드는 위 설정만으로 예전과 동일하게 동작한다.
// 배선은 ../BENCH_WIRING.md 2~3장(P2 커넥터, GPIO21/22)을 따른다.
// 켠 센서는 부팅 시 응답해야 device/status 의 sensor_capabilities 에 올라간다.

// GPIO21(SDA)/GPIO22(SCL)가 기본이며, 다른 핀을 쓸 때만 아래를 정의한다.
// #define I2C_SDA_PIN 21
// #define I2C_SCL_PIN 22

// BME280 온습도(기압 겸용). 켜면 DHT22를 대신하므로 DHT_ENABLED 0 이 필수다
// (둘 다 켜면 같은 temp 토픽에 두 값이 번갈아 발행되어 컴파일 단계에서 막는다).
// 주소는 0x76 또는 0x77 — 펌웨어가 둘 다 시도한다. DHT_PIN 은 그대로 비게 된다.
// #define DHT_ENABLED 0
// #define BME280_ENABLED 1

// BH1750 조도. farm/<zone>/telemetry/light_lux 로 발행되며 대시보드가 바로 받는다.
// 파이 허브는 이 토픽을 구독하지 않으므로 급수 판단에는 영향이 없다.
// #define BH1750_ENABLED 1

// ADS1115 4채널 16비트 ADC. 아날로그 센서가 ADC1 채널 수를 넘을 때 쓴다.
// SOIL_SOURCE_ADS1115 를 켜면 토양수분을 보드 내장 ADC 대신 여기서 읽는데,
// raw 스케일이 0~4095 에서 0~32767 로 바뀌므로 아래 SOIL_DRY_RAW/SOIL_WET_RAW 는
// 물론 허브 config.yaml 의 soil_raw_min/soil_raw_max 까지 반드시 다시 실측해야 한다.
// #define ADS1115_ENABLED 1
// #define SOIL_SOURCE_ADS1115 1
// #define ADS1115_SOIL_CHANNEL 0
// #define ADS1115_ADDRESS 0x48   // ADDR 핀으로 0x48~0x4B 중 선택
