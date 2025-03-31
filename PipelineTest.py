import requests
import json
from confluent_kafka import Producer

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

# ----------------------------
# Hàm đẩy dữ liệu từ API vào Kafka
def produce_api_data_to_kafka(kafka_bootstrap_servers):
    # Lấy dữ liệu từ API
    api_url = ("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json?"
               "includeTimeseries=true&hasTimeseries=WV&includeForecastTimeseries=true")
    response = requests.get(api_url)
    if response.status_code != 200:
        print("Failed to fetch API data, status code:", response.status_code)
        return
    stations = response.json()  # danh sách station

    # Sử dụng Confluent Kafka Producer
    conf = {
        'bootstrap.servers': 'kafka:9092'
    }
    producer = Producer(conf)

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

# ----------------------------
# Cấu hình Kafka và đẩy dữ liệu vào Kafka
kafka_bootstrap_servers = ["kafka:9092"]
produce_api_data_to_kafka(kafka_bootstrap_servers)

# ----------------------------
# Khởi tạo SparkSession với cấu hình kết nối đến Hive Metastore, Iceberg, HDFS và MinIO
spark = SparkSession.builder \
    .appName("PipelineTest") \
    .master("spark://spark-master:7077") \
    .config("spark.sql.warehouse.dir", "hdfs://namenode:9000/user/hive/warehouse") \
    .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
    .config("spark.sql.catalogImplementation", "hive") \
    .config("spark.hadoop.hive.metastore.uris", "thrift://hive-metastore:9083") \
    .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.iceberg.type", "hive") \
    .config("spark.sql.catalog.iceberg.uri", "thrift://hive-metastore:9083") \
    .config("spark.sql.catalog.iceberg.warehouse", "hdfs://namenode:9000/user/hive/warehouse") \
    .config("spark.sql.adaptive.enabled", "false") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

sc = spark.sparkContext
# Đảm bảo cấu hình Hadoop sử dụng đúng defaultFS (hdfs://namenode:9000)
sc._jsc.hadoopConfiguration().set("fs.defaultFS", "hdfs://namenode:9000")
# Cấu hình truy cập MinIO (sử dụng s3a)
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

print("Schema defined")

# ----------------------------
# Đọc dữ liệu stream từ Kafka
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", ",".join(kafka_bootstrap_servers)) \
    .option("subscribePattern", "timeseries_.*") \
    .option("startingOffsets", "earliest") \
    .load()

# Ép kiểu và parse JSON theo schema
kafka_df = kafka_df.selectExpr("CAST(value AS STRING) as value", "topic", "timestamp")
processed_df = kafka_df.withColumn("json_data", from_json(col("value"), full_schema)) \
                        .select("topic", "timestamp", "json_data.*")

# ----------------------------
# Ghi dữ liệu ra Parquet trên HDFS
hdfsParquetQuery = processed_df.writeStream \
    .format("parquet") \
    .option("path", "hdfs://namenode:9000/youruser/sensor-data-parquet") \
    .option("checkpointLocation", "/tmp/checkpoint/hdfs-sensor-data") \
    .start()

# Ghi dữ liệu ra Parquet trên MinIO (sử dụng giao thức s3a)
minioParquetQuery = processed_df.writeStream \
    .format("parquet") \
    .outputMode("append") \
    .option("path", "s3a://sensor-data-parquet/") \
    .option("checkpointLocation", "s3a://sensor-data-parquet/checkpoints/") \
    .start()

# ----------------------------
# Tạo bảng Iceberg sử dụng Hive Metastore (nếu chưa tồn tại)
spark.sql("""
CREATE TABLE IF NOT EXISTS iceberg.default.sensor_data_iceberg (
    topic STRING,
    timestamp TIMESTAMP,
    station STRUCT<
        uuid: STRING,
        number: STRING,
        shortname: STRING,
        longname: STRING,
        km: DOUBLE,
        agency: STRING,
        longitude: DOUBLE,
        latitude: DOUBLE,
        water: STRUCT<shortname: STRING, longname: STRING>
    >,
    timeseries STRUCT<
        shortname: STRING,
        longname: STRING,
        unit: STRING,
        equidistance: INT,
        gaugeZero: STRUCT<unit: STRING, value: DOUBLE, validFrom: STRING>,
        start: STRING,
        end: STRING
    >
)
USING iceberg
""")

icebergQuery = processed_df.writeStream \
    .format("iceberg") \
    .option("catalog", "iceberg") \
    .option("checkpointLocation", "/tmp/checkpoint/iceberg-sensor-data") \
    .start("iceberg.default.sensor_data_iceberg")  # Sử dụng identifier đầy đủ

# ----------------------------
# Ghi dữ liệu ra console để debug
consoleQuery = processed_df.writeStream \
    .format("console") \
    .option("truncate", "false") \
    .start()

# ----------------------------
# Truy xuất metadata từ Hive Metastore thông qua Spark Catalog
print("Databases in Hive Metastore:")
spark.catalog.listDatabases().show(truncate=False)
print("Tables in default database:")
spark.catalog.listTables("default").show(truncate=False)

spark.streams.awaitAnyTermination()
