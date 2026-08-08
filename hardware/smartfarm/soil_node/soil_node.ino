// Smartfarm 센서 노드 - ESP32 / ESP8266 공용
// 역할: 토양수분/온습도 읽어서 MQTT publish, 펌프 명령 MQTT subscribe.
// 로컬 안전장치: 허브(라즈베리파이)와 통신이 끊겨도 PUMP_MAX_RUN_MS를 넘기면 무조건 OFF.
//
// 필요 라이브러리 (Arduino Library Manager):
//   - PubSubClient (Nick O'Leary)
//   - DHT sensor library (Adafruit) + Adafruit Unified Sensor
//   - I2C 센서를 켠 경우에만: Adafruit BME280 Library / BH1750 / Adafruit ADS1X15
//     (+ Adafruit BusIO). config.h에서 끄면 링크되지 않는다.
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
#include "config.h"

// 토양수분 센서가 아직 배선되지 않은 구역을 위한 스위치.
// 미배선 ADC 핀은 floating이라 노이즈를 읽는데, 그 값이 soil로 publish되면
// 허브가 이를 진짜 건조 신호로 믿고 급수를 트리거한다 (2026-07-25 zone1 실제 발생:
// floating GPIO34 -> soil_pct=0 -> pump on). 센서 없는 구역은 아예 publish하지 않는다.
// 기존 config.h 호환을 위해 미정의 시 1(센서 있음)로 간주한다.
#ifndef SOIL_SENSOR_ENABLED
#define SOIL_SENSOR_ENABLED 1
#endif

// ── I2C 센서 확장 (기본 전부 꺼짐) ────────────────────────────────────────────
// 아래 매크로를 config.h에 정의하지 않으면 이 파일은 예전과 완전히 동일하게 동작한다.
// 배선 규격과 핀 매핑은 ../BENCH_WIRING.md 2~3장을 따른다.
#ifndef DHT_ENABLED
#define DHT_ENABLED 1          // 기존 노드 호환. BME280을 쓰면 0으로 내린다.
#endif
#ifndef BME280_ENABLED
#define BME280_ENABLED 0
#endif
#ifndef BH1750_ENABLED
#define BH1750_ENABLED 0
#endif
#ifndef ADS1115_ENABLED
#define ADS1115_ENABLED 0
#endif

#define I2C_ENABLED (BME280_ENABLED || BH1750_ENABLED || ADS1115_ENABLED)

#if I2C_ENABLED
// 보드별 기본 I2C 핀. config.h에서 덮어쓸 수 있다.
#ifndef I2C_SDA_PIN
#if defined(ESP32)
#define I2C_SDA_PIN 21
#else
#define I2C_SDA_PIN 4          // ESP8266 D2
#endif
#endif
#ifndef I2C_SCL_PIN
#if defined(ESP32)
#define I2C_SCL_PIN 22
#else
#define I2C_SCL_PIN 5          // ESP8266 D1
#endif
#endif
#endif

// 온습도 소스가 둘이면 같은 토픽에 두 값이 번갈아 발행되어 허브/대시보드가
// 원인을 알 수 없는 튀는 값을 보게 된다. 런타임에 조용히 어긋나게 두지 않고
// 컴파일 단계에서 막는다.
#if BME280_ENABLED && DHT_ENABLED
#error "온습도 소스가 둘입니다. BME280을 쓰려면 config.h에 #define DHT_ENABLED 0 을 추가하세요."
#endif
#if !BME280_ENABLED && !DHT_ENABLED
#warning "온습도 센서가 없습니다 (temp/humidity 미발행)."
#endif

// ADS1115를 토양수분 소스로 쓰면 raw 스케일이 보드 내장 ADC와 달라진다
// (ESP8266 0~1023 / ESP32 0~4095 → ADS1115 0~32767). SOIL_DRY_RAW/SOIL_WET_RAW는
// 물론 허브 config.yaml의 soil_raw_min/soil_raw_max도 반드시 다시 실측해야 한다.
#ifndef SOIL_SOURCE_ADS1115
#define SOIL_SOURCE_ADS1115 0
#endif
#if SOIL_SOURCE_ADS1115 && !ADS1115_ENABLED
#error "SOIL_SOURCE_ADS1115=1 이면 ADS1115_ENABLED 1 도 필요합니다."
#endif
#ifndef ADS1115_SOIL_CHANNEL
#define ADS1115_SOIL_CHANNEL 0
#endif
#ifndef ADS1115_ADDRESS
#define ADS1115_ADDRESS 0x48
#endif

#if DHT_ENABLED
#include <DHT.h>
#endif
#if I2C_ENABLED
#include <Wire.h>
#endif
#if BME280_ENABLED
#include <Adafruit_BME280.h>
#endif
#if BH1750_ENABLED
#include <BH1750.h>
#endif
#if ADS1115_ENABLED
#include <Adafruit_ADS1X15.h>
#endif

WiFiClient espClient;
PubSubClient mqtt(espClient);
#if DHT_ENABLED
DHT dht(DHT_PIN, DHT22);
#endif
#if BME280_ENABLED
Adafruit_BME280 bme;
bool bmeReady = false;
#endif
#if BH1750_ENABLED
BH1750 lightMeter;
bool lightReady = false;
#endif
#if ADS1115_ENABLED
Adafruit_ADS1115 ads;
bool adsReady = false;
#endif
#if I2C_ENABLED
// 부팅 스캔 결과. 센서를 하나씩 붙이며 검증할 때(BENCH_WIRING.md 7장 4번)
// 시리얼 모니터 없이 MQTT만으로 주소를 확인할 수 있도록 heartbeat에 실어 보낸다.
String i2cFound;
#endif

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
#if BH1750_ENABLED
// 조도는 기존 스칼라 토픽이 아니라 확장 경로로 보낸다. 대시보드가
// farm/+/telemetry/+ 를 구독하고 light_lux 를 유효 지표로 이미 인정한다
// (core/smartfarm_dashboard.py). 파이 허브는 이 토픽을 구독하지 않으므로
// 급수 판단에는 영향이 없다 — 조도로 물을 주지는 않는다.
char topicLight[80];
#endif

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
#if BH1750_ENABLED
  snprintf(topicLight, sizeof(topicLight), "farm/%s/telemetry/light_lux", ZONE_ID);
#endif
}

#if I2C_ENABLED
// 버스에 실제로 응답하는 주소만 남긴다. 배선을 바꾼 뒤 "센서가 안 읽힌다"가
// 배선 문제인지 라이브러리 문제인지 가르는 첫 번째 판정 도구다.
void i2cScan() {
  i2cFound = "";
  for (uint8_t addr = 0x08; addr < 0x78; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      char buf[8];
      snprintf(buf, sizeof(buf), "0x%02X", addr);
      if (i2cFound.length()) i2cFound += ",";
      i2cFound += buf;
    }
  }
  Serial.print("[i2c] SDA=GPIO");
  Serial.print(I2C_SDA_PIN);
  Serial.print(" SCL=GPIO");
  Serial.print(I2C_SCL_PIN);
  Serial.print(" found: ");
  Serial.println(i2cFound.length() ? i2cFound : "(없음 — 배선/전원 확인)");
}
#endif

// 온습도 소스를 한 곳으로 모은다. 호출부는 어느 센서가 달렸는지 몰라도 된다.
// 값을 못 읽으면 NAN을 채워 호출부가 발행을 건너뛰게 한다.
void readAmbient(float& temp, float& humidity) {
  temp = NAN;
  humidity = NAN;
#if BME280_ENABLED
  if (bmeReady) {
    temp = bme.readTemperature();
    humidity = bme.readHumidity();
  }
#elif DHT_ENABLED
  temp = dht.readTemperature();
  humidity = dht.readHumidity();
#endif
}

#if SOIL_SENSOR_ENABLED
// 토양수분 raw. ADS1115를 쓰면 16비트(0~32767) 스케일이라 캘리브레이션 값이
// 보드 내장 ADC와 전혀 다르다. 읽기 실패는 -1로 알린다.
int readSoilRaw() {
#if SOIL_SOURCE_ADS1115
  if (!adsReady) return -1;
  int16_t raw = ads.readADC_SingleEnded(ADS1115_SOIL_CHANNEL);
  return raw < 0 ? 0 : (int)raw;
#else
  return analogRead(SOIL_MOISTURE_PIN);
#endif
}
#endif

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
  payload += "\",\"board\":\"" + board + "\",\"firmware\":\"smartfarm-node-2.1\"";
  payload += ",\"boot_id\":\"" + bootId + "\",\"ip\":\"" + WiFi.localIP().toString() + "\"";
  payload += ",\"rssi_dbm\":" + String(WiFi.RSSI()) + ",\"uptime_s\":" + String(millis() / 1000);
  payload += ",\"watchdog_max_run_ms\":" + String(PUMP_MAX_RUN_MS);
  // 실제로 초기화에 성공한 센서만 신고한다. config.h에서 켰다는 사실이 아니라
  // 부팅 시 응답했다는 사실을 보고해야, 대시보드의 capabilities가 배선 상태를 반영한다.
  String caps = "";
#if DHT_ENABLED
  caps += "\"dht22\"";
#endif
#if BME280_ENABLED
  if (bmeReady) { if (caps.length()) caps += ","; caps += "\"bme280\""; }
#endif
#if BH1750_ENABLED
  if (lightReady) { if (caps.length()) caps += ","; caps += "\"bh1750\""; }
#endif
#if ADS1115_ENABLED
  if (adsReady) { if (caps.length()) caps += ","; caps += "\"ads1115\""; }
#endif
#if SOIL_SENSOR_ENABLED
  if (caps.length()) caps += ",";
  caps += "\"soil_adc\"";
#endif
  payload += ",\"sensor_capabilities\":[" + caps + "]";
#if I2C_ENABLED
  String i2cList = "";
  int from = 0;
  while (from < (int)i2cFound.length()) {
    int comma = i2cFound.indexOf(',', from);
    if (comma < 0) comma = i2cFound.length();
    if (i2cList.length()) i2cList += ",";
    i2cList += "\"" + i2cFound.substring(from, comma) + "\"";
    from = comma + 1;
  }
  payload += ",\"i2c\":[" + i2cList + "]";
#endif
  payload += ",\"actuator_capabilities\":[\"pump_relay\"],\"state\":\"" + String(state);
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
  float temp, humidity;
  readAmbient(temp, humidity);
  String payload = "{\"command_id\":\"" + commandId + "\",\"accepted\":true,\"phase\":\"result\"";
  payload += ",\"connectivity\":{\"wifi\":true,\"mqtt\":true,\"rssi_dbm\":" + String(WiFi.RSSI()) + "}";
#if BME280_ENABLED
  payload += ",\"bme280\":{\"pass\":" + String((bmeReady && !isnan(temp) && !isnan(humidity)) ? "true" : "false");
#elif DHT_ENABLED
  payload += ",\"dht22\":{\"pass\":" + String((!isnan(temp) && !isnan(humidity)) ? "true" : "false");
#else
  payload += ",\"ambient\":{\"pass\":false,\"reason\":\"no_sensor\"";
#endif
  if (!isnan(temp)) payload += ",\"temp_c\":" + String(temp, 1);
  if (!isnan(humidity)) payload += ",\"humidity_pct\":" + String(humidity, 1);
  payload += "}";
#if BH1750_ENABLED
  if (lightReady) {
    float lux = lightMeter.readLightLevel();
    payload += ",\"bh1750\":{\"pass\":" + String(lux >= 0 ? "true" : "false");
    if (lux >= 0) payload += ",\"light_lux\":" + String(lux, 1);
    payload += "}";
  } else {
    payload += ",\"bh1750\":{\"pass\":false,\"reason\":\"init_failed\"}";
  }
#endif
#if SOIL_SENSOR_ENABLED
  {
    // 읽기 실패(-1)를 pass:true 로 덮지 않는다. 대시보드는 pass:false 를 보고
    // diagnostic_failed 경보를 올리므로, 여기서 거짓 통과를 내면 고장이 묻힌다.
    int raw = readSoilRaw();
    payload += ",\"soil_adc\":{\"pass\":" + String(raw >= 0 ? "true" : "false");
    if (raw >= 0) payload += ",\"raw\":" + String(raw);
    payload += ",\"source\":\"" + String(SOIL_SOURCE_ADS1115 ? "ads1115" : "onboard_adc") + "\"}";
  }
#else
  payload += ",\"soil_adc\":{\"pass\":false,\"reason\":\"disabled\"}";
#endif
#if I2C_ENABLED
  // 진단 때마다 다시 스캔한다. 센서를 하나씩 붙이며 검증할 때 재부팅 없이
  // 원격에서 주소를 확인할 수 있는 경로다.
  i2cScan();
  payload += ",\"i2c_scan\":\"" + i2cFound + "\"";
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
#if DHT_ENABLED
  dht.begin();
#endif
#if I2C_ENABLED
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  i2cScan();
#endif
#if BME280_ENABLED
  // 모듈마다 주소가 0x76 또는 0x77이라 둘 다 시도한다.
  bmeReady = bme.begin(0x76) || bme.begin(0x77);
  Serial.println(bmeReady ? "[bme280] ok" : "[bme280] init 실패 — 주소/배선 확인");
#endif
#if BH1750_ENABLED
  lightReady = lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
  Serial.println(lightReady ? "[bh1750] ok" : "[bh1750] init 실패 — 주소/배선 확인");
#endif
#if ADS1115_ENABLED
  adsReady = ads.begin(ADS1115_ADDRESS);
  Serial.println(adsReady ? "[ads1115] ok" : "[ads1115] init 실패 — 주소/배선 확인");
#endif
  connectWifi();
  mqtt.setServer(MQTT_BROKER_HOST, MQTT_BROKER_PORT);
  // Device heartbeat and diagnostic JSON exceed PubSubClient's 256-byte
  // default packet limit. Without this, publish() silently returns false while
  // legacy scalar telemetry keeps working, creating a false "old firmware"
  // appearance in the dashboard.
  mqtt.setBufferSize(1024);
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

    float temp, humidity;
    readAmbient(temp, humidity);

    Serial.print("[debug] ambient temp=");
    Serial.print(temp);
    Serial.print(" humidity=");
    Serial.println(humidity);
    if (isnan(temp) || isnan(humidity)) {
      Serial.println("[error] 온습도 읽기 실패");
    }

    char buf[16];
#if SOIL_SENSOR_ENABLED
    int soilRaw = readSoilRaw();
    Serial.print("[debug] soil raw=");
    Serial.println(soilRaw);

    // 읽기 실패(-1)는 발행하지 않는다. 발행하면 허브가 이를 실측값으로 믿고
    // 급수를 판단한다 — 값이 없는 것과 0인 것은 다르다.
    if (soilRaw >= 0) {
      // raw를 soil보다 먼저 발행한다. MQTT는 하나의 연결 안에서 발행 순서를 보존하므로,
      // 허브가 soil(급수 판단을 트리거하는 토픽)을 처리하는 시점에는 같은 주기의 raw가
      // 이미 도착해 있다. 순서가 바뀌면 허브가 직전 주기의 낡은 raw로 검증하게 된다.
      snprintf(buf, sizeof(buf), "%d", soilRaw);
      mqtt.publish(topicSoilRaw, buf);

      snprintf(buf, sizeof(buf), "%d", soilPercentFromRaw(soilRaw));
      mqtt.publish(topicSoil, buf);
    } else {
      Serial.println("[error] 토양수분 읽기 실패 — soil 미발행");
    }
#else
    Serial.println("[info] SOIL_SENSOR_ENABLED=0 — soil 미발행 (허브 급수 트리거 없음)");
#endif

#if BH1750_ENABLED
    if (lightReady) {
      float lux = lightMeter.readLightLevel();
      Serial.print("[debug] light lux=");
      Serial.println(lux);
      if (lux >= 0) {
        dtostrf(lux, 4, 1, buf);
        mqtt.publish(topicLight, buf);
      }
    }
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
