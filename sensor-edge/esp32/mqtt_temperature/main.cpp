/**
 * GDF-AutoMon: Temperature & Humidity Sensor (SHT31) → MQTT
 *
 * Hardware: ESP32 + SHT31 sensor (I2C: SDA=21, SCL=22)
 * Libraries: WiFi, PubSubClient, Adafruit_SHT31
 *
 * Publishes to:
 *   gdf/{SENSOR_ID}/temperature  {"value": 22.5, "unit": "°C", "ts": "<epoch>"}
 *   gdf/{SENSOR_ID}/humidity     {"value": 61.2, "unit": "%RH", "ts": "<epoch>"}
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <Adafruit_SHT31.h>
#include <ArduinoJson.h>
#include <time.h>

// ─── Configuration ───────────────────────────────────────────────────────────
#define WIFI_SSID     "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define MQTT_HOST     "192.168.1.100"   // IP of your server running EMQX
#define MQTT_PORT     1883
#define MQTT_USER     "sensor001"
#define MQTT_PASS     "sensor_secret"
#define SENSOR_ID     "sensor-temp-001" // Must be unique per sensor
#define PUBLISH_INTERVAL_MS 10000       // 10 seconds between readings
// ─────────────────────────────────────────────────────────────────────────────

Adafruit_SHT31 sht31;
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

char topicTemp[64];
char topicHumidity[64];

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\nWiFi connected: %s\n", WiFi.localIP().toString().c_str());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");
    String clientId = String("esp32-") + SENSOR_ID;
    if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
      Serial.println("connected");
    } else {
      Serial.printf("failed (rc=%d), retrying in 5s\n", mqtt.state());
      delay(5000);
    }
  }
}

void publishReading(const char* topic, float value, const char* unit) {
  StaticJsonDocument<128> doc;
  doc["value"] = value;
  doc["unit"] = unit;
  doc["ts"] = (long)time(nullptr);
  doc["sensor_id"] = SENSOR_ID;

  char payload[128];
  serializeJson(doc, payload);
  mqtt.publish(topic, payload, /*retained=*/true);
  Serial.printf("Published %s → %s\n", topic, payload);
}

void setup() {
  Serial.begin(115200);
  snprintf(topicTemp,     sizeof(topicTemp),     "gdf/%s/temperature", SENSOR_ID);
  snprintf(topicHumidity, sizeof(topicHumidity), "gdf/%s/humidity",    SENSOR_ID);

  connectWifi();

  // Sync NTP time
  configTime(0, 0, "pool.ntp.org");

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setBufferSize(512);

  if (!sht31.begin(0x44)) {
    Serial.println("SHT31 not found! Check wiring.");
    while (true) delay(1000);
  }
  Serial.println("SHT31 initialized");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  float temp = sht31.readTemperature();
  float hum  = sht31.readHumidity();

  if (!isnan(temp) && !isnan(hum)) {
    publishReading(topicTemp,     temp, "°C");
    publishReading(topicHumidity, hum,  "%RH");
  } else {
    Serial.println("SHT31 read error");
  }

  delay(PUBLISH_INTERVAL_MS);
}
