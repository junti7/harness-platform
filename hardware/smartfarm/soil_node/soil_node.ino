// Smartfarm 센서 노드 - ESP32 / ESP8266 공용
// 역할: 토양수분/온습도 읽어서 MQTT publish, 펌프 명령 MQTT subscribe.
// 로컬 안전장치: 허브(라즈베리파이)와 통신이 끊겨도 PUMP_MAX_RUN_MS를 넘기면 무조건 OFF.
//
// 필요 라이브러리 (Arduino Library Manager):
//   - PubSubClient (Nick O'Leary)
//   - DHT sensor library (Adafruit) + Adafruit Unified Sensor
//
// 구역 추가 시: 보드에 맞는 config.example.esp32.h 또는 config.example.esp8266.h를
// config.h로 복사 -> ZONE_ID/MQTT_CLIENT_ID만 바꿔서 재플래싱.

#if defined(ESP32)
#include <WiFi.h>
#elif defined(ESP8266)
#include <ESP8266WiFi.h>
#else
#error "ESP32 또는 ESP8266 보드 core로만 컴파일 가능"
#endif
#include <PubSubClient.h>
#include <DHT.h>
#include "config.h"

// 토양수분 센서가 아직 배선되지 않은 구역을 위한 스위치.
// 미배선 ADC 핀은 floating이라 노이즈를 읽는데, 그 값이 soil로 publish되면
// 허브가 이를 진짜 건조 신호로 믿고 급수를 트리거한다 (2026-07-25 zone1 실제 발생:
// floating GPIO34 -> soil_pct=0 -> pump on). 센서 없는 구역은 아예 publish하지 않는다.
// 기존 config.h 호환을 위해 미정의 시 1(센서 있음)로 간주한다.
#ifndef SOIL_SENSOR_ENABLED
#define SOIL_SENSOR_ENABLED 1
#endif

WiFiClient espClient;
PubSubClient mqtt(espClient);
DHT dht(DHT_PIN, DHT22);

bool pumpOn = false;
unsigned long pumpStartedAt = 0;
unsigned long lastSensorRead = 0;

char topicSoil[64];
char topicTemp[64];
char topicHumidity[64];
char topicPumpCmd[64];
char topicPumpStatus[64];

void buildTopics() {
  snprintf(topicSoil, sizeof(topicSoil), "farm/%s/soil", ZONE_ID);
  snprintf(topicTemp, sizeof(topicTemp), "farm/%s/temp", ZONE_ID);
  snprintf(topicHumidity, sizeof(topicHumidity), "farm/%s/humidity", ZONE_ID);
  snprintf(topicPumpCmd, sizeof(topicPumpCmd), "farm/%s/pump/cmd", ZONE_ID);
  snprintf(topicPumpStatus, sizeof(topicPumpStatus), "farm/%s/pump/status", ZONE_ID);
}

void setPump(bool on) {
  pumpOn = on;
  digitalWrite(PUMP_RELAY_PIN, on ? HIGH : LOW);
  pumpStartedAt = on ? millis() : 0;
  mqtt.publish(topicPumpStatus, on ? "on" : "off", true);
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  if (strcmp(topic, topicPumpCmd) == 0) {
    if (msg == "on") setPump(true);
    else if (msg == "off") setPump(false);
  }
}

void connectWifi() {
  Serial.print("[wifi] connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.print("\n[wifi] connected, ip=");
  Serial.println(WiFi.localIP());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("[mqtt] connecting to ");
    Serial.print(MQTT_BROKER_HOST);
    Serial.println("...");
    if (mqtt.connect(MQTT_CLIENT_ID)) {
      Serial.println("[mqtt] connected");
      mqtt.subscribe(topicPumpCmd);
    } else {
      Serial.print("[mqtt] failed, state=");
      Serial.println(mqtt.state());
      delay(2000);
    }
  }
}

int readSoilPercent() {
  int raw = analogRead(SOIL_MOISTURE_PIN);
  Serial.print("[debug] A0 raw=");
  Serial.println(raw);
  int pct = map(raw, SOIL_DRY_RAW, SOIL_WET_RAW, 0, 100);
  return constrain(pct, 0, 100);
}

void setup() {
  Serial.begin(115200);
  pinMode(PUMP_RELAY_PIN, OUTPUT);
  digitalWrite(PUMP_RELAY_PIN, LOW);

  buildTopics();
  dht.begin();
  connectWifi();
  mqtt.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
  mqtt.setCallback(onMqttMessage);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  // 로컬 안전장치: 허브 응답 여부와 무관하게 최대 런타임 초과 시 강제 OFF
  if (pumpOn && millis() - pumpStartedAt > PUMP_MAX_RUN_MS) {
    setPump(false);
  }

  unsigned long now = millis();
  if (now - lastSensorRead >= SENSOR_READ_INTERVAL_MS) {
    lastSensorRead = now;

    float temp = dht.readTemperature();
    float humidity = dht.readHumidity();

    Serial.print("[debug] DHT22 GPIO");
    Serial.print(DHT_PIN);
    Serial.print(" temp=");
    Serial.print(temp);
    Serial.print(" humidity=");
    Serial.println(humidity);
    if (isnan(temp) || isnan(humidity)) {
      Serial.println("[error] DHT22 read failed");
    }

    char buf[16];
#if SOIL_SENSOR_ENABLED
    int soilPct = readSoilPercent();
    snprintf(buf, sizeof(buf), "%d", soilPct);
    mqtt.publish(topicSoil, buf);
#else
    Serial.println("[info] SOIL_SENSOR_ENABLED=0 — soil 미발행 (허브 급수 트리거 없음)");
#endif

    if (!isnan(temp)) {
      dtostrf(temp, 4, 1, buf);
      mqtt.publish(topicTemp, buf);
    }
    if (!isnan(humidity)) {
      dtostrf(humidity, 4, 1, buf);
      mqtt.publish(topicHumidity, buf);
    }
  }
}
