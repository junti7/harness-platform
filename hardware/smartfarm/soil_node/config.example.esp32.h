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
