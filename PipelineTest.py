import requests
import json
from kafka import KafkaProducer
from confluent_kafka import Producer

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

def produce_api_data_to_kafka(kafka_bootstrap_servers):
    # Lấy dữ liệu từ API
    api_url = ("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json?"
               "includeTimeseries=true&hasTimeseries=WV&includeForecastTimeseries=true")
    response = requests.get(api_url)
    if response.status_code != 200:
        print("Failed to fetch API data, status code:", response.status_code)
        return
    stations = response.json()  # danh sách station

    # Khởi tạo Kafka producer
    # producer = KafkaProducer(
    #     bootstrap_servers=kafka_bootstrap_servers,
    #     value_serializer=lambda v: json.dumps(v).encode('utf-8')
    # )
    
    conf = {
    'bootstrap.servers': 'kafka:9092'
    }   
    producer = Producer(conf)

    # Với mỗi station, gửi từng record cho từng timeseries vào Kafka topic riêng
    for station in stations:
        # Lấy thông tin station chung
        station_data = {
            "uuid": station.get("uuid"),
            "number": station.get("number"),
            "shortname": station.get("shortname"),
            "longname": station.get("longname"),
            "km": station.get("km"),
            "agency": station.get("agency"),
            "longitude": station.get("longitude"),
            "latitude": station.get("latitude"),
            "water": station.get("water")
        }
        timeseries_list = station.get("timeseries", [])
        for ts in timeseries_list:
            record = {
                "station": station_data,
                "timeseries": ts
            }
            # Đặt tên topic theo kiểu: timeseries_<shortname của timeseries>
            topic = "timeseries_" + ts.get("shortname", "unknown")
            producer.produce(topic, json.dumps(record).encode('utf-8'))
    producer.flush()
    print("API data produced to Kafka topics.")


# Cấu hình Kafka
kafka_bootstrap_servers = ["kafka:9092"]

# Bước 1: Lấy dữ liệu từ API và đẩy vào Kafka (nhiều topic)
produce_api_data_to_kafka(kafka_bootstrap_servers)

# ----------------------------
# Khởi tạo SparkSession, ép warehouse dir cho Hive phù hợp với core-site.xml (port 8020)
spark = SparkSession.builder \
    .appName("PipelineTest") \
    .master("spark://spark-master:7077") \
    .config("spark.sql.warehouse.dir", "hdfs://namenode:8020/user/hive/warehouse") \
    .getOrCreate()
# spark.sparkContext.setLogLevel("WARN")

sc = spark.sparkContext
# Set the MinIO access key, secret key, endpoint, and other configurations
sc._jsc.hadoopConfiguration().set("fs.s3a.access.key", "test")
sc._jsc.hadoopConfiguration().set("fs.s3a.secret.key", "12345678")
sc._jsc.hadoopConfiguration().set("fs.s3a.endpoint", "http://minio:9000")
sc._jsc.hadoopConfiguration().set("fs.s3a.path.style.access", "true")
sc._jsc.hadoopConfiguration().set("fs.s3a.connection.ssl.enabled", "false")
sc._jsc.hadoopConfiguration().set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")

# ----------------------------
# Định nghĩa schema cho dữ liệu JSON
station_schema = StructType([
    StructField("uuid", StringType()),
    StructField("number", StringType()),
    StructField("shortname", StringType()),
    StructField("longname", StringType()),
    StructField("km", DoubleType()),
    StructField("agency", StringType()),
    StructField("longitude", DoubleType()),
    StructField("latitude", DoubleType()),
    StructField("water", StructType([
        StructField("shortname", StringType()),
        StructField("longname", StringType())
    ]))
])

timeseries_schema = StructType([
    StructField("shortname", StringType()),
    StructField("longname", StringType()),
    StructField("unit", StringType()),
    StructField("equidistance", IntegerType()),
    # Các trường tùy chọn
    StructField("gaugeZero", StructType([
        StructField("unit", StringType()),
        StructField("value", DoubleType()),
        StructField("validFrom", StringType())
    ]), True),
    StructField("start", StringType(), True),
    StructField("end", StringType(), True)
])

full_schema = StructType([
    StructField("station", station_schema),
    StructField("timeseries", timeseries_schema)
])

# ----------------------------
# Đọc stream từ Kafka:
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", ",".join(kafka_bootstrap_servers)) \
    .option("subscribePattern", "timeseries_.*") \
    .option("startingOffsets", "earliest") \
    .load()

kafka_df = kafka_df.selectExpr("CAST(value AS STRING) as value", "topic", "timestamp")
processed_df = kafka_df.withColumn("json_data", from_json(col("value"), full_schema)) \
                        .select("topic", "timestamp", "json_data.*")

# ----------------------------
# Ghi dữ liệu ra file Parquet:
hdfsParquetQuery = processed_df.writeStream \
    .format("parquet") \
    .option("path", "hdfs://namenode:8020/youruser/sensor_data_parquet") \
    .option("checkpointLocation", "/tmp/checkpoint/hdfs_sensor_data") \
    .trigger(processingTime="10 seconds") \
    .start()
minioParquetQuery = processed_df.writeStream \
    .format("parquet") \
    .outputMode("append") \
    .option("path", "s3a://sensor-data-parquet/") \
    .option("checkpointLocation", "s3a://sensor-data-parquet/checkpoints/") \
    .start()


# ----------------------------
# # Ghi dữ liệu ra bảng Iceberg (sử dụng Hive Catalog) cho 2 nguồn lưu trữ:
# hdfsIcebergQuery = processed_df.writeStream \
#     .format("parquet") \
#     .option("catalog", "hive") \
#     .option("path", "hdfs://namenode:8020/youruser/hdfs_sensor_data_iceberg") \
#     .option("checkpointLocation", "/tmp/checkpoint/hive_hdfs_sensor_data") \
#     .trigger(processingTime="10 seconds") \
#     .start()

# minioIcebergQuery = processed_df.writeStream \
#     .format("iceberg") \
#     .option("catalog", "hive") \
#     .option("path", "minio_sensor_data_iceberg") \
#     .option("checkpointLocation", "/tmp/checkpoint/hive_minio_sensor_data") \
#     .trigger(processingTime="10 seconds") \
#     .start()

# ----------------------------
# Ghi ra console để debug
consoleQuery = processed_df.writeStream \
    .format("console") \
    .option("truncate", "false") \
    .trigger(processingTime="10 seconds") \
    .start()

hdfsParquetQuery.awaitTermination()
minioParquetQuery.awaitTermination()
# hdfsIcebergQuery.awaitTermination()
# minioIcebergQuery.awaitTermination()
consoleQuery.awaitTermination()
