// ESP8266 노드 설정 템플릿 (10비트 ADC, 0~1023 raw 범위 — ESP32와 캘리브레이션 값이 다르다).
// 이 파일을 config.h로 복사한 뒤 실제 값을 채운다. config.h는 git에 커밋하지 않는다.
#pragma once

#define WIFI_SSID "your-wifi-ssid"
#define WIFI_PASSWORD "your-wifi-password"

#define MQTT_BROKER_HOST "192.168.1.x"   // 라즈베리파이 IP (Mosquitto 구동 위치)
#define MQTT_BROKER_PORT 1883
#define MQTT_CLIENT_ID "smartfarm-zone2"

// 구역을 늘릴 때는 노드마다 이 값만 바꿔서 새 config.h로 플래싱한다.
#define ZONE_ID "zone2"

// ESP8266은 아날로그 입력이 A0 하나뿐이다 (GPIO 번호 지정 불가).
#define SOIL_MOISTURE_PIN A0
// D1(GPIO5)/D2(GPIO4)는 I2C(SCL/SDA) 표준 핀이므로 센서 확장용으로 비워둔다.
// DHT/릴레이는 부팅 스트래핑 제약이 없는 D5~D7을 쓴다 (D3/D4/D8은 스트래핑 핀이라 금지).
// 근거와 전체 매핑: ../BENCH_WIRING.md 3장
#define DHT_PIN 13        // D7 — 외부 10kΩ 풀업 필요
#define PUMP_RELAY_PIN 14 // D5

// 토양수분 센서를 아직 배선하지 않았다면 반드시 0으로 둔다.
// 미배선 ADC 핀은 floating이라 노이즈를 읽고, 그 값이 soil로 발행되면 허브가
// 진짜 건조 신호로 믿고 급수를 트리거한다 (2026-07-25 zone1에서 실제 발생).
#define SOIL_SENSOR_ENABLED 1

// 토양 수분 ADC 원시값 캘리브레이션 (센서/토양마다 실측 후 조정, ESP8266은 0~1023 범위)
#define SOIL_DRY_RAW 750        // 완전 건조 상태 raw 값
#define SOIL_WET_RAW 300        // 물에 담갔을 때 raw 값

// 로컬 안전장치 — 허브(MQTT)가 응답 없어도 노드 단독으로 지킨다.
#define PUMP_MAX_RUN_MS 15000UL       // 한 번 켜지면 최대 15초 후 강제 OFF
#define SENSOR_READ_INTERVAL_MS 30000UL
