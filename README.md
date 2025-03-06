# ESP32 MQTT with HiveMQ Cloud and Kafka in Docker Tutorial

This guide explains how to set up your ESP32 DEV Module using PlatformIO to connect to HiveMQ Cloud via MQTT. Follow the steps below to create a new PlatformIO project, flash your ESP32, and verify the connection.

---

## Prerequisites

- **PlatformIO IDE**: Install the PlatformIO extension for Visual Studio Code from [PlatformIO](https://platformio.org/platformio-ide).
- **Docker Desktop**: Required for running the Kafka cluster and Kafka Connect. Download from [Docker Official Website](https://www.docker.com/products/docker-desktop).
- **Terminal (PowerShell, CMD, or VS Code integrated terminal)**: For running Docker and Kafka commands.
- **HiveMQ Cloud Account**: Sign up at [HiveMQ Cloud](https://www.hivemq.com/cloud/) and note your broker URL, username, and password.
- **Wi-Fi Access**: Needed for the ESP32 to connect to HiveMQ Cloud.

---

## Step 1: Set Up the ESP32 DEV Module with PlatformIO

### 1.1 Install and Configure PlatformIO

- **Install the Extension**: Add the PlatformIO IDE extension in Visual Studio Code.
- **Configure Boards**:  
  Open PlatformIO Home, then navigate to **Boards**.  
  If necessary, add the ESP32 boards by including the following URL in your settings:
  ```
  https://dl.espressif.com/dl/package_esp32_index.json
  ```

### 1.2 Create a New PlatformIO Project

- **New Project**: In PlatformIO Home, click **New Project**.
- **Project Settings**:
  - **Name**: e.g., `ESP32_MQTT`
  - **Board**: Select **ESP32 Dev Module**
  - **Framework**: Choose **Arduino**
- Click **Finish**. PlatformIO will generate the project structure.

### 1.3 Add the Firmware Code

- **Edit Code**: Open `src/main.cpp` and replace its content with the code below.  
  Update the placeholders with your actual Wi-Fi and HiveMQ Cloud credentials.

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

  // etc...
  ```

### 1.4 Build and Upload the Firmware

- **Connect Hardware**: Plug your ESP32 DEV Module into your computer via USB.
- **Build the Project**: In the PlatformIO sidebar, click the **Build** button to compile your project.
- **Upload the Firmware**: After a successful build, click the **Upload** button to flash your ESP32.
- **Monitor Output**: Watch the terminal output for build and upload progress.

### 1.5 Monitor the Serial Output

- **Serial Monitor**: Open the Serial Monitor in PlatformIO by clicking the Serial Monitor icon or using the command palette.
- **Baud Rate**: Set it to 115200.
- **Verify Connection**: Check that your ESP32 connects to your Wi-Fi network and successfully establishes a connection with the HiveMQ Cloud broker.

> **Note**: Ensure your ESP32 publishes data to the `/esp32/` topic on HiveMQ Cloud.

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
  cd .\simple_IOTgateway\docker
  ```
### 3.2 Run the Kafka Cluster and Kafka Connect
- Start the Docker containers in detached mode:
  ```
  docker compose up -d
  ```
- Verify all containers are running:
  ```
  docker ps
  ```
  You should see `kafk-1`, `kafk-2`, `kafk-3`, and `connect`.

### 3.3 Install the MQTT Source Connector
- Access the Kafka Connect container:
  ```
  docker exec -it connect bash
  ```
- Install the MQTT connector:
  ```
  confluent-hub install confluentinc/kafka-connect-mqtt:latest
  ```
- When prompted, select option `2` (e.g., `/usr/share/confluent-hub-components`) and complete the installation.
- Exit the container:
  ```
  exit
  ```
- Restart Kafka Connect to load the connector:
  ```
  docker compose restart connect
  ```

### 3.4 Configure the MQTT Source Connector
- In the `docker` directory, direct int a file named `mqtt-source.json`
- Replace `YOUR_HIVEMQ_BROKER_URL`, `YOUR_HIVEMQ_USERNAME`, and `YOUR_HIVEMQ_PASSWORD` with your actual HiveMQ Cloud credentials.

### 3.5 Create the Connector
- In PowerShell (preferred due to JSON handling), run:
  ```
  $json = Get-Content -Path ".\mqtt-source.json" -Raw
  Invoke-WebRequest -Method Post -Headers @{"Content-Type" = "application/json"} -Body $json -Uri "http://localhost:8083/connectors"
  ```
- Alternatively, in CMD with `curl` (if installed):
  ```
  curl -X POST -H "Content-Type: application/json" --data @mqtt-source.json http://localhost:8083/connectors
  ```

---

## Step 4: Verify the Data Flow

- Use an MQTT client (e.g., MQTT Explorer) to publish a test message to `/esp32/` on HiveMQ Cloud.
- Consume the data from Kafka in CMD:
  ```
  docker exec -it kafk-1 /opt/kafka/bin/kafka-console-consumer.sh --topic "esp32_data" --bootstrap-server kafk-1:9092,kafk-2:9092,kafk-3:9092 --from-beginning
  ```
- You should see messages that has been encoded by base64 like this:
  ```
  "eyJ0aW1lc3RhbXAiOiIyMDI1LTAzLTA2VDA0OjMyOjE4WiIsInRlbXBlcmF0dXJlIjowLCJodW1pZGl0eSI6MCwic29pbF9tb2lzdHVyZSI6MjMxNywibGlnaHQiOjE1NTZ9"
  ```
--- 
