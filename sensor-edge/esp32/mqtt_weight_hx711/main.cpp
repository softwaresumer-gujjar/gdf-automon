/**
 * GDF-AutoMon: Weight / Load Cell (HX711) → MQTT
 *
 * Hardware: ESP32 + HX711 breakout + load cell
 *   DOUT → GPIO 4, SCK → GPIO 5
 *
 * Publishes to:
 *   gdf/{SENSOR_ID}/weight  {"value": 4.21, "unit": "kg", "ts": "<epoch>"}
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <HX711.h>
#include <ArduinoJson.h>
#include <time.h>

// ─── Configuration ───────────────────────────────────────────────────────────
#define WIFI_SSID       "YOUR_WIFI_SSID"
#define WIFI_PASSWORD   "YOUR_WIFI_PASSWORD"
#define MQTT_HOST       "192.168.1.100"
#define MQTT_PORT       1883
#define MQTT_USER       "sensor002"
#define MQTT_PASS       "sensor_secret"
#define SENSOR_ID       "sensor-weight-001"
#define HX711_DOUT_PIN  4
#define HX711_SCK_PIN   5
#define CALIBRATION_FACTOR  2280.0  // Adjust per calibration (grams/raw_unit)
#define PUBLISH_INTERVAL_MS 5000
// ─────────────────────────────────────────────────────────────────────────────

HX711 scale;
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);
char topicWeight[64];

void connectWifi() {
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) delay(500);
  Serial.printf("WiFi: %s\n", WiFi.localIP().toString().c_str());
}

void connectMqtt() {
  while (!mqtt.connected()) {
    if (mqtt.connect(("esp32-" + String(SENSOR_ID)).c_str(), MQTT_USER, MQTT_PASS))
      Serial.println("MQTT connected");
    else
      delay(5000);
  }
}

void setup() {
  Serial.begin(115200);
  snprintf(topicWeight, sizeof(topicWeight), "gdf/%s/weight", SENSOR_ID);

  connectWifi();
  configTime(0, 0, "pool.ntp.org");
  mqtt.setServer(MQTT_HOST, MQTT_PORT);

  scale.begin(HX711_DOUT_PIN, HX711_SCK_PIN);
  scale.set_scale(CALIBRATION_FACTOR);
  scale.tare();  // Zero the scale on startup
  Serial.println("HX711 initialized and tared");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  if (scale.is_ready()) {
    float weightGrams = scale.get_units(5);  // Average of 5 readings
    float weightKg = weightGrams / 1000.0;

    StaticJsonDocument<128> doc;
    doc["value"] = weightKg;
    doc["unit"] = "kg";
    doc["ts"] = (long)time(nullptr);
    doc["sensor_id"] = SENSOR_ID;
    doc["raw_grams"] = weightGrams;

    char payload[128];
    serializeJson(doc, payload);
    mqtt.publish(topicWeight, payload, true);
    Serial.printf("Weight: %.3f kg\n", weightKg);
  }

  delay(PUBLISH_INTERVAL_MS);
}
