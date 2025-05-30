import requests
import json
from confluent_kafka import Producer

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, hash, when
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, DoubleType
)

def produce_api_data_to_kafka(kafka_bootstrap_servers):
    api_url = ("https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json?"
               "includeTimeseries=true&hasTimeseries=WV&includeForecastTimeseries=true")
    response = requests.get(api_url)
    if response.status_code != 200:
        print("Failed to fetch API data, status code:", response.status_code)
        return
    stations = response.json() 

    conf = {'bootstrap.servers': 'kafka:9092'}
    producer = Producer(conf)

    for station in stations:
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
            topic = "timeseries_" + ts.get("shortname", "unknown")
            producer.produce(topic, json.dumps(record).encode('utf-8'))
    producer.flush()
    print("API data produced to Kafka topics.")

kafka_bootstrap_servers = ["kafka:9092"]
produce_api_data_to_kafka(kafka_bootstrap_servers)

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
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
sc = spark.sparkContext
sc._jsc.hadoopConfiguration().set("fs.defaultFS", "hdfs://namenode:9000")
sc._jsc.hadoopConfiguration().set("fs.s3a.access.key", "test")
sc._jsc.hadoopConfiguration().set("fs.s3a.secret.key", "12345678")
sc._jsc.hadoopConfiguration().set("fs.s3a.endpoint", "http://minio:9000")
sc._jsc.hadoopConfiguration().set("fs.s3a.path.style.access", "true")
sc._jsc.hadoopConfiguration().set("fs.s3a.connection.ssl.enabled", "false")
sc._jsc.hadoopConfiguration().set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")

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

kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", ",".join(kafka_bootstrap_servers)) \
    .option("subscribePattern", "timeseries_.*") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .load()

kafka_df = kafka_df.selectExpr("CAST(value AS STRING) as value", "topic", "timestamp")
processed_df = kafka_df.withColumn("json_data", from_json(col("value"), full_schema)) \
                        .select("topic", "timestamp", "json_data.*")


processed_df = processed_df.withColumn("storage_type", 
                        when((hash(col("station.uuid")) % 2) == 0, "hdfs").otherwise("minio"))

hdfs_df = processed_df.filter(col("storage_type") == "hdfs")
minio_df = processed_df.filter(col("storage_type") == "minio")

hdfsQuery = hdfs_df.writeStream \
    .format("parquet") \
    .option("path", "hdfs://namenode:9000/youruser/sensor-data-parquet-hdfs") \
    .option("checkpointLocation", "/tmp/checkpoint/hdfs-sensor-data") \
    .start()

minioQuery = minio_df.writeStream \
    .format("parquet") \
    .option("path", "s3a://sensor-data-parquet-minio/") \
    .option("checkpointLocation", "s3a://sensor-data-parquet-minio/checkpoints/") \
    .start()

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

# Combine metadata.
hdfs_data = spark.readStream \
    .format("parquet") \
    .schema(full_schema) \
    .load("hdfs://namenode:9000/youruser/sensor-data-parquet-hdfs")

minio_data = spark.readStream \
    .format("parquet") \
    .schema(full_schema) \
    .load("s3a://sensor-data-parquet-minio/")

unified_data = hdfs_data.union(minio_data)

icebergQuery = unified_data.writeStream \
    .format("iceberg") \
    .option("catalog", "iceberg") \
    .option("checkpointLocation", "/tmp/checkpoint/iceberg-sensor-data") \
    .outputMode("append") \
    .start("iceberg.default.sensor_data_iceberg")

consoleQuery = processed_df.writeStream \
    .format("console") \
    .option("truncate", "false") \
    .start()

print("Databases in Hive Metastore:")
spark.createDataFrame(spark.catalog.listDatabases()).show(truncate=False)
print("Tables in default database:")
tables = spark.catalog.listTables("default")
tables_data = [(t.name, t.tableType, t.isTemporary) for t in tables]
spark.createDataFrame(tables_data, schema=["name", "tableType", "isTemporary"]).show(truncate=False)

spark.streams.awaitAnyTermination()
