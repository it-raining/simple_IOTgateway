#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT20.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <time.h>

// WiFi credentials (replace with your own)
const char* ssid = "ACLAB";
const char* password = "ACLAB2023";

// MQTT broker details (replace with your HiveMQ Cloud credentials)
const char* mqtt_server = "5a6b7a5064ab4e2f8065a560661324cc.s1.eu.hivemq.cloud";  // Your HiveMQ Cloud host
const int mqtt_port = 8883;  // Secure port
const char* mqtt_user = "1khoaho";
const char* mqtt_password = "Hdk31415";
const char* root_topic = "/esp32/";  // Root topic for data

// Sensor pins
#define SOIL_MOISTURE_PIN 34
#define LIGHT_PIN 35

WiFiClientSecure espClient;
PubSubClient client(espClient);
DHT20 dht20;

void setup() {
  Serial.begin(115200);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");

  configTime(0, 0, "pool.ntp.org");
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.println("Waiting for time sync...");
    delay(1000);
  }
  Serial.println("Time synced!");
  espClient.setInsecure(); // Allow insecure connection for testing purposes
  client.setServer(mqtt_server, mqtt_port);

  Wire.begin();
  dht20.begin();
}

void connectMQTT() {
  while (!client.connected()) {
    Serial.println("Connecting to MQTT...");
    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_password)) {
      Serial.println("Connected to MQTT!");
    } else {
      Serial.print("Failed to connect, MQTT state: ");
      Serial.println(client.state());

      if (client.state() == -2) {
        Serial.println("SSL/TLS handshake failed. Check CA certificate or setInsecure().");
      } else if (client.state() == 5) {
        Serial.println("Authentication failed! Check MQTT username/password.");
      } else if (client.state() == -1) {
        Serial.println("Connection timeout. Check server availability.");
      }

      Serial.println("Retrying in 5 seconds...");
      delay(4999);
    }
  }
}


void loop() {
  if (!client.connected()) {
    connectMQTT();
  }
  client.loop();

  // Get current UTC time
  time_t now;
  struct tm timeinfo;
  time(&now);
  gmtime_r(&now, &timeinfo);  // Use UTC time

  char timestamp[25];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &timeinfo); // Format timestamp as "YYYY-MM-DDTHH:MM:SSZ"
  // Read sensor data
  float temperature = dht20.getTemperature();
  float humidity = dht20.getHumidity();
  int soil_moisture = analogRead(SOIL_MOISTURE_PIN);
  int light = analogRead(LIGHT_PIN);

  // Create JSON object
  JsonDocument doc;
  doc["timestamp"] = timestamp;
  doc["temperature"] = temperature;
  doc["humidity"] = humidity;
  doc["soil_moisture"] = soil_moisture;
  doc["light"] = light;

  // Serialize JSON to string
  char jsonBuffer[256];
  serializeJson(doc, jsonBuffer);

  // Publish to MQTT topic
  client.publish(root_topic, jsonBuffer);

  Serial.println("Published sensor data:");
  Serial.println(jsonBuffer);
  delay(5000);  // Publish every 5 seconds
}