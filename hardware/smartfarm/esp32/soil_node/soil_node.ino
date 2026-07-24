// Smartfarm 1구역 프로토타입 - ESP32 센서 노드
// 역할: 토양수분/온습도 읽어서 MQTT publish, 펌프 명령 MQTT subscribe.
// 로컬 안전장치: 허브(라즈베리파이)와 통신이 끊겨도 PUMP_MAX_RUN_MS를 넘기면 무조건 OFF.
//
// 필요 라이브러리 (Arduino Library Manager):
//   - PubSubClient (Nick O'Leary)
//   - DHT sensor library (Adafruit) + Adafruit Unified Sensor
//
// 구역 추가 시: config.example.h를 새 config.h로 복사 -> ZONE_ID/MQTT_CLIENT_ID만 바꿔서 재플래싱.

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include "config.h"

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
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void connectMqtt() {
  while (!mqtt.connected()) {
    if (mqtt.connect(MQTT_CLIENT_ID)) {
      mqtt.subscribe(topicPumpCmd);
    } else {
      delay(2000);
    }
  }
}

int readSoilPercent() {
  int raw = analogRead(SOIL_MOISTURE_PIN);
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

    int soilPct = readSoilPercent();
    float temp = dht.readTemperature();
    float humidity = dht.readHumidity();

    char buf[16];
    snprintf(buf, sizeof(buf), "%d", soilPct);
    mqtt.publish(topicSoil, buf);

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
