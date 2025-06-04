# IoT Data Pipeline Gateway

A consolidated IoT data pipeline that collects sensor data from IoT devices with API fallback, streams through Kafka, processes with Spark, and stores in dual format (MinIO & HDFS) using Iceberg metadata layer with Hive metastore catalog.

## Architecture

```
IoT Devices/API → Kafka → Spark Streaming → MinIO/HDFS (Parquet) → Iceberg → Hive Metastore
```

### Components

- **IoT Gateway**: Single Python application for data collection and pipeline orchestration
- **Kafka**: Message streaming platform
- **Spark**: Distributed data processing engine with streaming
- **MinIO**: S3-compatible object storage
- **HDFS**: Hadoop distributed file system
- **Iceberg**: Table format providing ACID transactions and schema evolution
- **Hive Metastore**: Metadata catalog for Iceberg tables

## Features

- **Automatic Fallback**: IoT device data collection with API fallback
- **Real-time Streaming**: Kafka-based data streaming
- **Dual Storage**: Concurrent storage to MinIO and HDFS in Parquet format
- **Unified Metadata**: Iceberg tables with Hive metastore catalog
- **Data Partitioning**: Automatic date-based partitioning
- **Health Monitoring**: Built-in system validation and monitoring

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.8+

### Setup

1. Start the infrastructure:
```bash
cd docker
docker-compose up -d
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the IoT Gateway:
```bash
python iot_gateway.py --mode stream --data-source iot
```

### Usage Modes

- **System Validation**: `python iot_gateway.py --mode validate`
- **Data Streaming**: `python iot_gateway.py --mode stream --data-source iot`
- **API Fallback**: `python iot_gateway.py --mode stream --data-source api`
- **Data Summary**: `python iot_gateway.py --mode summary`

### Data Flow

1. **Collection**: IoT devices provide sensor data (temperature, humidity, soil moisture, light)
2. **Fallback**: If IoT unavailable, weather API data is used
3. **Streaming**: Data flows through Kafka topic `sensor_data`
4. **Processing**: Spark streaming processes and enriches data
5. **Storage**: Parallel writes to MinIO and HDFS in Parquet format
6. **Metadata**: Iceberg provides unified table interface via Hive metastore

### Monitoring

Access web interfaces:

- Spark Master: http://localhost:8080
- HDFS NameNode: http://localhost:9870
- MinIO Console: http://localhost:9001
- Kafka Connect: http://localhost:8083

### Data Query

Query unified data through Iceberg:

```python
spark.sql("SELECT * FROM hive_prod.default.sensor_data WHERE partition_date = '2024-01-01'").show()
```

### Container Services

- kafka: Message broker
- namenode/datanode: HDFS storage
- hive-metastore: Metadata catalog
- minio: Object storage
- spark-master/worker: Processing engine
- kafka-connect: Data connectors

## Configuration

Edit `docker/docker-compose.yml` to modify service configurations.

The IoT Gateway automatically configures Spark with:
- Iceberg integration
- Hive metastore catalog
- MinIO S3 compatibility
- HDFS connectivity

## Development

The single `iot_gateway.py` file contains all functionality:
- IoT data collection simulation
- Weather API integration  
- Kafka producer/consumer
- Spark streaming setup
- Iceberg table management
- Dual storage writes
- System health checks

# Unified IoT Pipeline

File Python duy nhất gộp tất cả chức năng của hệ thống IoT Gateway với 2 chế độ hoạt động:

## Kiến trúc hệ thống

- **Chế độ IoT**: Thu thập dữ liệu từ thiết bị ESP32 qua MQTT
- **Chế độ API**: Thu thập dữ liệu từ API pegelonline.wsv.de
- **Kafka**: Message broker cho dữ liệu streaming
- **Spark**: Xử lý dữ liệu và lưu trữ
- **HDFS + MinIO**: 2 nơi lưu trữ dữ liệu dưới dạng Parquet
- **Hive Metastore + Iceberg**: Quản lý metadata và truy xuất thống nhất

## Sử dụng

### 1. Chạy pipeline với dữ liệu API (mặc định)

```bash
python unified_iot_pipeline.py --mode api --action run
```

### 2. Chạy pipeline với dữ liệu IoT

```bash
python unified_iot_pipeline.py --mode iot --action run
```

### 3. Truy xuất và kiểm tra dữ liệu

```bash
python unified_iot_pipeline.py --action query
```

## Luồng hoạt động

1. **Kiểm tra hệ thống**: Validate containers và services
2. **Thu thập dữ liệu**: Từ IoT hoặc API theo chế độ đã chọn
3. **Gửi qua Kafka**: Streaming data vào Kafka topic
4. **Spark Processing**: Sử dụng `docker exec spark-submit` để xử lý
5. **Lưu trữ kép**: 
   - HDFS: `hdfs://namenode:9000/user/unified-sensor-data-hdfs/`
   - MinIO: `s3a://sensor-data-minio/`
6. **Iceberg Table**: `hive_prod.default.unified_sensor_data`
7. **Truy xuất thống nhất**: Query 2 storage như 1 nơi duy nhất

## Cấu trúc dữ liệu

### IoT Data (ESP32)
```json
{
  "device_id": "ESP32_001",
  "timestamp": "2024-06-03T10:00:00Z",
  "temperature": 25.5,
  "humidity": 60.0,
  "soil_moisture": 450,
  "light": 800,
  "location": {
    "latitude": 10.762622,
    "longitude": 106.660172
  }
}
```

### API Data (Pegelonline)
```json
{
  "station_uuid": "e6d68ab7-5c27-4f25-896f-11dbf04056cd",
  "station_number": "10089006",
  "shortname": "VILSHOFEN",
  "longitude": 13.182429,
  "latitude": 48.637297,
  "water_shortname": "DONAU",
  "timeseries_data": [...]
}
```

## Containers cần thiết

- kafka
- namenode, datanode
- hive-metastore, hive-metastore-postgresql
- minio
- spark-master, spark-worker

## Cách chạy

**Chạy file Python ở ngoài** (không dùng spark-submit):

```bash
python unified_iot_pipeline.py --mode api
```

File sẽ tự động:
1. Tạo Spark job script
2. Copy vào Spark master container
3. Thực hiện `docker exec spark-submit`
4. Quản lý toàn bộ pipeline

## Tính năng chính

- ✅ Kiểm tra health của toàn bộ hệ thống
- ✅ Thu thập dữ liệu từ 2 nguồn khác nhau
- ✅ Streaming qua Kafka
- ✅ Xử lý Spark thông qua docker exec
- ✅ Lưu trữ song song HDFS + MinIO
- ✅ Truy xuất thống nhất qua Iceberg
- ✅ Query performance testing
- ✅ Graceful shutdown với Ctrl+C 