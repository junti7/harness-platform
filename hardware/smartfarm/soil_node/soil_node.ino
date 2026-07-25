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
unsigned long lastHeartbeat = 0;
unsigned long lastCommandSequence = 0;
String bootId;

char topicSoil[64];
char topicSoilRaw[64];
char topicTemp[64];
char topicHumidity[64];
char topicPumpCmd[64];
char topicPumpStatus[64];
char topicDeviceStatus[80];
char topicCommandRequest[80];
char topicCommandAck[80];
char topicDiagnosticRequest[80];
char topicDiagnosticResult[80];

void buildTopics() {
  snprintf(topicSoil, sizeof(topicSoil), "farm/%s/soil", ZONE_ID);
  snprintf(topicSoilRaw, sizeof(topicSoilRaw), "farm/%s/soil_raw", ZONE_ID);
  snprintf(topicTemp, sizeof(topicTemp), "farm/%s/temp", ZONE_ID);
  snprintf(topicHumidity, sizeof(topicHumidity), "farm/%s/humidity", ZONE_ID);
  snprintf(topicPumpCmd, sizeof(topicPumpCmd), "farm/%s/pump/cmd", ZONE_ID);
  snprintf(topicPumpStatus, sizeof(topicPumpStatus), "farm/%s/pump/status", ZONE_ID);
  snprintf(topicDeviceStatus, sizeof(topicDeviceStatus), "farm/%s/device/status", ZONE_ID);
  snprintf(topicCommandRequest, sizeof(topicCommandRequest), "farm/%s/command/request", ZONE_ID);
  snprintf(topicCommandAck, sizeof(topicCommandAck), "farm/%s/command/ack", ZONE_ID);
  snprintf(topicDiagnosticRequest, sizeof(topicDiagnosticRequest), "farm/%s/diagnostic/request", ZONE_ID);
  snprintf(topicDiagnosticResult, sizeof(topicDiagnosticResult), "farm/%s/diagnostic/result", ZONE_ID);
}

void setPump(bool on) {
  pumpOn = on;
  digitalWrite(PUMP_RELAY_PIN, on ? HIGH : LOW);
  pumpStartedAt = on ? millis() : 0;
  mqtt.publish(topicPumpStatus, on ? "on" : "off", true);
}

String jsonStringValue(const String& json, const char* key) {
  String marker = "\"" + String(key) + "\"";
  int keyAt = json.indexOf(marker);
  if (keyAt < 0) return "";
  int colon = json.indexOf(':', keyAt + marker.length());
  int quote = json.indexOf('"', colon + 1);
  if (colon < 0 || quote < 0) return "";
  int end = json.indexOf('"', quote + 1);
  if (end < 0) return "";
  return json.substring(quote + 1, end);
}

unsigned long jsonUnsignedValue(const String& json, const char* key, unsigned long fallback) {
  String marker = "\"" + String(key) + "\"";
  int keyAt = json.indexOf(marker);
  if (keyAt < 0) return fallback;
  int colon = json.indexOf(':', keyAt + marker.length());
  if (colon < 0) return fallback;
  int start = colon + 1;
  while (start < (int)json.length() && (json[start] == ' ' || json[start] == '\"')) start++;
  int end = start;
  while (end < (int)json.length() && isDigit(json[end])) end++;
  if (end == start) return fallback;
  return (unsigned long)json.substring(start, end).toInt();
}

void publishAck(const String& commandId, bool accepted, const char* phase, const char* reason) {
  if (commandId.length() == 0 || commandId.length() > 64) return;
  String payload = "{\"command_id\":\"" + commandId + "\",\"accepted\":";
  payload += accepted ? "true" : "false";
  payload += ",\"phase\":\"" + String(phase) + "\",\"reason\":\"" + String(reason);
  payload += "\",\"observed_state\":\"" + String(pumpOn ? "on" : "off") + "\",\"ts\":";
  payload += String((unsigned long)(millis() / 1000));
  payload += "}";
  mqtt.publish(topicCommandAck, payload.c_str(), false);
}

void publishHeartbeat(const char* state) {
#if defined(ESP32)
  String board = "ESP32";
  uint64_t chip = ESP.getEfuseMac();
  char chipBuf[20];
  snprintf(chipBuf, sizeof(chipBuf), "%04X%08X", (uint16_t)(chip >> 32), (uint32_t)chip);
#else
  String board = "ESP8266";
  char chipBuf[20];
  snprintf(chipBuf, sizeof(chipBuf), "%06X", ESP.getChipId());
#endif
  String payload = "{\"device_id\":\"" + String(MQTT_CLIENT_ID) + "\",\"kind\":\"";
#if defined(ESP32)
  payload += "esp32";
#else
  payload += "esp8266";
#endif
  payload += "\",\"board\":\"" + board + "\",\"firmware\":\"smartfarm-node-2.0\"";
  payload += ",\"boot_id\":\"" + bootId + "\",\"ip\":\"" + WiFi.localIP().toString() + "\"";
  payload += ",\"rssi_dbm\":" + String(WiFi.RSSI()) + ",\"uptime_s\":" + String(millis() / 1000);
  payload += ",\"watchdog_max_run_ms\":" + String(PUMP_MAX_RUN_MS);
  payload += ",\"sensor_capabilities\":[\"dht22\"";
#if SOIL_SENSOR_ENABLED
  payload += ",\"soil_adc\"";
#endif
  payload += "],\"actuator_capabilities\":[\"pump_relay\"],\"state\":\"" + String(state);
  payload += "\",\"ts\":" + String(millis() / 1000) + "}";
  mqtt.publish(topicDeviceStatus, payload.c_str(), true);
}

void handleStructuredCommand(const String& msg) {
  String commandId = jsonStringValue(msg, "command_id");
  String kind = jsonStringValue(msg, "kind");
  unsigned long sequence = jsonUnsignedValue(msg, "sequence", 0);
  if (commandId.length() == 0 || sequence == 0 || sequence <= lastCommandSequence) {
    publishAck(commandId, false, "rejected", "missing_or_stale_sequence");
    return;
  }
  // Record sequence before actuation so QoS1 duplicates cannot execute twice.
  lastCommandSequence = sequence;
  if (kind == "pump_off") {
    setPump(false);
    publishAck(commandId, true, "completed", "observed_off");
    return;
  }
  if (kind == "pump_on") {
    unsigned long durationS = jsonUnsignedValue(msg, "duration_s", 0);
    if (durationS == 0 || durationS * 1000UL >= PUMP_MAX_RUN_MS) {
      publishAck(commandId, false, "rejected", "duration_exceeds_watchdog");
      return;
    }
    setPump(true);
    publishAck(commandId, true, "completed", "watchdog_armed");
    return;
  }
  publishAck(commandId, false, "rejected", "unsupported_command");
}

void handleDiagnostic(const String& msg) {
  String commandId = jsonStringValue(msg, "command_id");
  if (commandId.length() == 0) return;
  float temp = dht.readTemperature();
  float humidity = dht.readHumidity();
  String payload = "{\"command_id\":\"" + commandId + "\",\"accepted\":true,\"phase\":\"result\"";
  payload += ",\"connectivity\":{\"wifi\":true,\"mqtt\":true,\"rssi_dbm\":" + String(WiFi.RSSI()) + "}";
  payload += ",\"dht22\":{\"pass\":" + String((!isnan(temp) && !isnan(humidity)) ? "true" : "false");
  if (!isnan(temp)) payload += ",\"temp_c\":" + String(temp, 1);
  if (!isnan(humidity)) payload += ",\"humidity_pct\":" + String(humidity, 1);
  payload += "}";
#if SOIL_SENSOR_ENABLED
  payload += ",\"soil_adc\":{\"pass\":true,\"raw\":" + String(analogRead(SOIL_MOISTURE_PIN)) + "}";
#else
  payload += ",\"soil_adc\":{\"pass\":false,\"reason\":\"disabled\"}";
#endif
  payload += ",\"pump_state\":\"" + String(pumpOn ? "on" : "off") + "\",\"ts\":" + String(millis() / 1000) + "}";
  mqtt.publish(topicDiagnosticResult, payload.c_str(), false);
}

void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  if (length > 2048) return;
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];

  if (strcmp(topic, topicPumpCmd) == 0) {
    if (msg == "on") setPump(true);
    else if (msg == "off") setPump(false);
  } else if (strcmp(topic, topicCommandRequest) == 0) {
    handleStructuredCommand(msg);
  } else if (strcmp(topic, topicDiagnosticRequest) == 0) {
    handleDiagnostic(msg);
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
    String willPayload = "{\"device_id\":\"" + String(MQTT_CLIENT_ID) + "\",\"state\":\"offline\",\"boot_id\":\"" + bootId + "\"}";
    if (mqtt.connect(MQTT_CLIENT_ID, topicDeviceStatus, 1, true, willPayload.c_str())) {
      Serial.println("[mqtt] connected");
      // Clear accidental retained control requests before subscribing. Commands are
      // never intentionally retained; an empty retained publish deletes broker state.
      mqtt.publish(topicCommandRequest, "", true);
      mqtt.publish(topicDiagnosticRequest, "", true);
      delay(25);
      mqtt.subscribe(topicPumpCmd, 1);
      // Structured pump intent is consumed only by the Raspberry Pi hub so
      // its cooldown/sensor-fault/ZoneState rules cannot be bypassed.
      mqtt.subscribe(topicDiagnosticRequest, 1);
      publishHeartbeat("online");
    } else {
      Serial.print("[mqtt] failed, state=");
      Serial.println(mqtt.state());
      delay(2000);
    }
  }
}

// raw를 퍼센트로 변환한다. constrain 때문에 고장난 센서의 극단값도 0 또는 100이라는
// "정상으로 보이는" 값이 되므로, 고장 판정은 퍼센트가 아니라 raw로 해야 한다.
// 그래서 허브가 검증할 수 있도록 raw를 별도 토픽으로 함께 발행한다.
int soilPercentFromRaw(int raw) {
  int pct = map(raw, SOIL_DRY_RAW, SOIL_WET_RAW, 0, 100);
  return constrain(pct, 0, 100);
}

void setup() {
  Serial.begin(115200);

  // 펌프 핀을 출력으로 잡기 전에, 이 핀이 어떤 상태로 떠 있었는지 먼저 읽어 남긴다.
  // setup()이 실행되기까지 수십~수백 ms 동안은 펌웨어가 핀을 제어하지 못하는데,
  // 그 사이 릴레이가 물리면 부팅할 때마다 펌프가 잠깐씩 돈다. 새 구역을 배선한 뒤
  // 이 로그가 HIGH면(= active-HIGH 릴레이 기준) 펌프를 연결하기 전에
  // GPIO-GND 사이 풀다운 저항(10k)으로 잡아야 한다.
  // 주의: 이건 부팅 직후의 '안정 상태'를 보는 것이라, 더 짧은 순간의 글리치까지
  // 잡아내지는 못한다. 릴레이를 눈으로 확인하는 절차를 대체하지 않는다.
  pinMode(PUMP_RELAY_PIN, INPUT);
  Serial.print("\n[boot] pump pin GPIO");
  Serial.print(PUMP_RELAY_PIN);
  Serial.print(" resting state = ");
  Serial.println(digitalRead(PUMP_RELAY_PIN) ? "HIGH (relay may engage at boot)" : "LOW (safe)");

  pinMode(PUMP_RELAY_PIN, OUTPUT);
  digitalWrite(PUMP_RELAY_PIN, LOW);

  buildTopics();
#if defined(ESP32)
  bootId = String((uint32_t)(ESP.getEfuseMac() & 0xFFFFFFFF), HEX) + "-" + String(micros(), HEX);
#else
  bootId = String(ESP.getChipId(), HEX) + "-" + String(micros(), HEX);
#endif
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
  if (now - lastHeartbeat >= 30000UL) {
    lastHeartbeat = now;
    publishHeartbeat("online");
  }
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
    int soilRaw = analogRead(SOIL_MOISTURE_PIN);
    Serial.print("[debug] soil raw=");
    Serial.println(soilRaw);

    // raw를 soil보다 먼저 발행한다. MQTT는 하나의 연결 안에서 발행 순서를 보존하므로,
    // 허브가 soil(급수 판단을 트리거하는 토픽)을 처리하는 시점에는 같은 주기의 raw가
    // 이미 도착해 있다. 순서가 바뀌면 허브가 직전 주기의 낡은 raw로 검증하게 된다.
    snprintf(buf, sizeof(buf), "%d", soilRaw);
    mqtt.publish(topicSoilRaw, buf);

    snprintf(buf, sizeof(buf), "%d", soilPercentFromRaw(soilRaw));
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
