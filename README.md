# simple_IOTgateway

## Overview

The `simple_IOTgateway` project demonstrates a basic IoT data pipeline where an ESP32 DEV Module collects sensor data (e.g., temperature, humidity) and publishes it to an MQTT topic on HiveMQ Cloud. The data is then ingested into a local 3-node Kafka cluster running in Docker using Kafka Connect. This setup enables real-time data streaming from the ESP32 to Kafka via HiveMQ Cloud without exposing your public IP.

### Components
- **ESP32 DEV Module**: Collects and publishes sensor data to HiveMQ Cloud.
- **HiveMQ Cloud**: A managed MQTT broker that receives data from the ESP32.
- **Kafka Cluster**: A 3-node Kafka cluster running locally in Docker to store the data.
- **Kafka Connect**: A connector that bridges HiveMQ Cloud and the Kafka cluster.

---

## Prerequisites

- **Arduino IDE**: For flashing the ESP32. Download from [Arduino Official Website](https://www.arduino.cc/en/software).
- **Docker Desktop**: For running the Kafka cluster and Kafka Connect. Download from [Docker Official Website](https://www.docker.com/products/docker-desktop).
- **PowerShell or CMD**: For running Docker and Kafka commands.
- **HiveMQ Cloud Account**: Sign up at [HiveMQ Cloud](https://www.hivemq.com/cloud/) and note your broker URL, username, and password.
- **Wi-Fi Access**: For the ESP32 to connect to HiveMQ Cloud.

---

## Step 1: Set Up the ESP32 DEV Module

### 1.1 Install Arduino IDE
- Download and install the Arduino IDE.
- Open the Arduino IDE and go to **File > Preferences**.
- In the "Additional Boards Manager URLs" field, add:
  ```
  https://dl.espressif.com/dl/package_esp32_index.json
  ```
- Go to **Tools > Board > Boards Manager**, search for "ESP32," and install the ESP32 board package.

### 1.2 Flash the ESP32
- Connect your ESP32 DEV Module to your computer via USB.
- In the Arduino IDE, select **Tools > Board > ESP32 Dev Module**.
- Use the following code (replace placeholders with your Wi-Fi and HiveMQ Cloud credentials):
  ```cpp
  #include <WiFi.h>
  #include <PubSubClient.h>

  // Wi-Fi credentials
  const char* ssid = "YOUR_WIFI_SSID";
  const char* password = "YOUR_WIFI_PASSWORD";

  // HiveMQ Cloud credentials
  const char* mqtt_server = "YOUR_HIVEMQ_BROKER_URL"; // e.g., abc123.s1.eu.hivemq.cloud
  const int mqtt_port = 8883; // Default for SSL
  const char* mqtt_user = "YOUR_HIVEMQ_USERNAME";
  const char* mqtt_pass = "YOUR_HIVEMQ_PASSWORD";
    // direct into ./ESP32_MQTT/src/main.cpp for further info  
  ```
- Replace `YOUR_WIFI_SSID`, `YOUR_WIFI_PASSWORD`, `YOUR_HIVEMQ_BROKER_URL`, `YOUR_HIVEMQ_USERNAME`, and `YOUR_HIVEMQ_PASSWORD` with your actual credentials.
- Click the **Upload** button to flash the code to your ESP32.
- Open the Serial Monitor (**Tools > Serial Monitor**) at 115200 baud to verify the ESP32 connects to Wi-Fi and HiveMQ Cloud.

**Note**: Ensure your ESP32 is publishing data to the `/esp32/` topic on HiveMQ Cloud.

---

## Step 2: Install Docker

- Download and install Docker Desktop for Windows.
- Follow the installation prompts. If prompted, enable WSL2 (Windows Subsystem for Linux 2).
- After installation, open a Command Prompt (CMD) or PowerShell and verify Docker is installed:
  ```
  docker --version
  ```
- If Docker Desktop doesn’t start, ensure Hyper-V is enabled:
  - Open **Control Panel > Programs > Turn Windows features on or off**.
  - Check **Hyper-V** and click **OK**.

---

## Step 3: Run Docker Compose

### 3.1 Navigate to the Docker Directory
- Open CMD or PowerShell and change to your project’s Docker directory (adjust the path as needed):
  ```
  cd D:\git_workspace\simple_IOTgateway\docker
  ```

### 3.2 Create the Docker Compose File
- Direct into a file named `docker-compose.yml` in the `docker` directory.

### 3.3 Run the Kafka Cluster and Kafka Connect
- Start the Docker containers in detached mode:
  ```
  docker compose up -d
  ```
- Verify all containers are running:
  ```
  docker ps
  ```
  You should see `kafk-1`, `kafk-2`, `kafk-3`, and `connect`.

### Deploying the Connectors

Once your Kafka Connect container is running with the connectors installed, you can deploy each connector using PowerShell’s `Invoke-RestMethod` (or any HTTP client). For example, to create the MQTT Source Connector:

```powershell
$json = Get-Content -Path ".\mqtt-source.json" -Raw
Invoke-RestMethod -Method Post -Headers @{"Content-Type"="application/json"} -Body $json -Uri "http://localhost:8083/connectors"
```

And then similarly for the HDFS Sink Connector:

```powershell
$json = Get-Content -Path ".\hdfs-sink.json" -Raw
Invoke-RestMethod -Method Post -Headers @{"Content-Type"="application/json"} -Body $json -Uri "http://localhost:8083/connectors"
```
### Checking the Connectors
docker exec -it connect ls /usr/share/confluent-hub-components

---


## Step 4: Verify the Data Flow

- Use an MQTT client (e.g., MQTT Explorer) to publish a test message to `/esp32/` on HiveMQ Cloud.
- Create topic from Kafka
    ```
    docker exec -it kafk-1 /opt/kafka/bin/kafka-topics.sh --create --topic esp32_data --bootstrap-server kafk-1:9092   
    ```
- Consume the data from Kafka in CMD:
  ```
  docker exec -it kafk-1 /opt/kafka/bin/kafka-console-consumer.sh --topic "esp32_data" --bootstrap-server kafk-1:9092,kafk-2:9092,kafk-3:9092 --from-beginning
  ```
- You should see messages that has been encoded by base64 like this:
  ```
  "eyJ0aW1lc3RhbXAiOiIyMDI1LTAzLTA2VDA0OjMyOjE4WiIsInRlbXBlcmF0dXJlIjowLCJodW1pZGl0eSI6MCwic29pbF9tb2lzdHVyZSI6MjMxNywibGlnaHQiOjE1NTZ9"
  ```

---

## Conclusion

You’ve successfully set up the `simple_IOTgateway` project! Your ESP32 is now sending data to HiveMQ Cloud, and Kafka is ingesting it locally via Docker. If you encounter issues, double-check your credentials, network settings, or container logs (`docker logs <container_name>`). Enjoy your IoT data pipeline!

--- 