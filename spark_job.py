#!/usr/bin/env python3

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, when, hash, expr, current_timestamp, lit
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType
import time
import traceback

def create_spark_session():
    try:
        spark = SparkSession.builder \
            .appName("IoTPipeline") \
            .master("spark://spark-master:7077") \
            .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.4,org.apache.hadoop:hadoop-aws:3.3.4,org.apache.hadoop:hadoop-common:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1") \
            .config("spark.sql.adaptive.enabled", "false") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "false") \
            .config("spark.driver.memory", "512m") \
            .config("spark.executor.memory", "512m") \
            .config("spark.executor.cores", "1") \
            .config("spark.cores.max", "1") \
            .config("spark.default.parallelism", "1") \
            .config("spark.sql.shuffle.partitions", "1") \
            .config("spark.sql.streaming.forceDeleteTempCheckpointLocation", "true") \
            .config("spark.sql.streaming.stopGracefullyOnShutdown", "true") \
            .config("spark.sql.streaming.stopActiveRunOnRestart", "true") \
            .config("spark.dynamicAllocation.enabled", "false") \
            .config("spark.streaming.stopGracefullyOnShutdown", "true") \
            .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
            .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
            .config("spark.hadoop.fs.s3a.access.key", "test") \
            .config("spark.hadoop.fs.s3a.secret.key", "12345678") \
            .config("spark.hadoop.fs.s3a.path.style.access", "true") \
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
            .config("spark.hadoop.fs.s3a.connection.timeout", "200000") \
            .config("spark.hadoop.fs.s3a.connection.establish.timeout", "40000") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkSessionCatalog") \
            .config("spark.sql.catalog.spark_catalog.type", "hive") \
            .config("spark.sql.catalog.spark_catalog.uri", "thrift://hive-metastore:9083") \
            .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
            .config("spark.sql.catalog.iceberg_catalog.type", "hive") \
            .config("spark.sql.catalog.iceberg_catalog.uri", "thrift://hive-metastore:9083") \
            .config("spark.sql.catalog.iceberg_catalog.warehouse", "hdfs://namenode:9000/user/hive/warehouse") \
            .enableHiveSupport() \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        print("=== SPARK SESSION WITH ICEBERG CREATED SUCCESSFULLY ===")
        return spark
    except Exception as e:
        print(f"=== FAILED TO CREATE SPARK SESSION: {e} ===")
        traceback.print_exc()
        return None

def define_schema():
    return StructType([
        StructField("device_id", StringType(), True),
        StructField("station_uuid", StringType(), True),
        StructField("timestamp", StringType(), True),
        StructField("temperature", DoubleType(), True),
        StructField("humidity", DoubleType(), True),
        StructField("soil_moisture", IntegerType(), True),
        StructField("light", IntegerType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("station_number", StringType(), True),
        StructField("shortname", StringType(), True),
        StructField("longname", StringType(), True),
        StructField("km", DoubleType(), True),
        StructField("agency", StringType(), True),
        StructField("water_shortname", StringType(), True),
        StructField("water_longname", StringType(), True),
        StructField("processed_timestamp", DoubleType(), True)
    ])

def create_hive_iceberg_table(spark):
    try:
        print("=== CREATING ICEBERG TABLE WITH HIVE METASTORE ===")
        
        spark.sql("CREATE DATABASE IF NOT EXISTS sensor_db")
        spark.sql("USE sensor_db")
        
        spark.sql("DROP TABLE IF EXISTS sensor_db.unified_sensor_data")
        
        spark.sql("""
            CREATE TABLE IF NOT EXISTS sensor_db.unified_sensor_data (
                record_id string,
                device_id string,
                station_uuid string,
                timestamp string,
                temperature double,
                humidity double,
                soil_moisture int,
                light int,
                latitude double,
                longitude double,
                station_number string,
                shortname string,
                longname string,
                km double,
                agency string,
                water_shortname string,
                water_longname string,
                processed_timestamp double,
                storage_location string,
                data_source string,
                kafka_timestamp timestamp,
                ingestion_date date
            ) 
            USING ICEBERG
            PARTITIONED BY (data_source, ingestion_date)
            LOCATION 'hdfs://namenode:9000/user/hive/warehouse/sensor_db/unified_sensor_data'
            TBLPROPERTIES (
                'write.parquet.compression-codec' = 'snappy',
                'write.metadata.metrics.default' = 'full'
            )
        """)
        
        print("=== ICEBERG TABLE CREATED SUCCESSFULLY ===")
        return True
        
    except Exception as e:
        print(f"=== ERROR CREATING ICEBERG TABLE: {e} ===")
        traceback.print_exc()
        return False

def run_pipeline(spark):
    try:
        print("=== STARTING KAFKA STREAM READING ===")
        schema = define_schema()
        
        kafka_df = spark.readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", "kafka:9092") \
            .option("subscribe", "sensor_data") \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .option("kafka.consumer.timeout.ms", "60000") \
            .option("kafka.session.timeout.ms", "30000") \
            .option("kafka.request.timeout.ms", "40000") \
            .option("maxOffsetsPerTrigger", "100") \
            .load()

        print("=== KAFKA STREAM CREATED, PARSING JSON ===")
        
        value_df = kafka_df.select(
            col("key").cast("string").alias("record_key"),
            col("value").cast("string").alias("json_data"),
            col("timestamp").alias("kafka_timestamp")
        )

        parsed_df = value_df.select(
            col("record_key"),
            from_json(col("json_data"), schema).alias("data"),
            col("kafka_timestamp")
        ).select(
            "record_key",
            "data.*",
            "kafka_timestamp"
        )

        enriched_df = parsed_df.withColumn(
            "storage_location",
            when(expr("abs(hash(concat(coalesce(record_key, ''), coalesce(station_uuid, ''), coalesce(timestamp, ''))))") % 2 == 0, "HDFS").otherwise("MinIO")
        ).withColumn(
            "data_source",
            when(col("device_id").isNotNull(), "IoT").otherwise("API")
        ).withColumn(
            "record_id",
            expr("uuid()")
        ).withColumn(
            "ingestion_date",
            expr("current_date()")
        )

        def write_batch(df, epoch_id):
            try:
                batch_count = df.count()
                print(f"=== PROCESSING BATCH {epoch_id} WITH {batch_count} RECORDS ===")
                
                if batch_count > 0:
                    df.cache()
                    
                    try:
                        df.write.mode("append").saveAsTable("sensor_db.unified_sensor_data")
                        print(f"=== SAVED {batch_count} RECORDS TO UNIFIED ICEBERG TABLE ===")
                    except Exception as e:
                        print(f"=== ICEBERG TABLE WRITE ERROR: {e} ===")
                    
                    hdfs_data = df.filter(col("storage_location") == "HDFS")
                    minio_data = df.filter(col("storage_location") == "MinIO")
                    
                    hdfs_count = hdfs_data.count()
                    minio_count = minio_data.count()
                    
                    if hdfs_count > 0:
                        try:
                            current_date = expr("date_format(current_timestamp(), 'yyyy-MM-dd')").alias("partition_date")
                            hdfs_data_with_date = hdfs_data.withColumn("partition_date", current_date)
                            partition_date = hdfs_data_with_date.first()['partition_date']
                            hdfs_path = f"hdfs://namenode:9000/user/sensor-data/date={partition_date}"
                            hdfs_data_with_date.write.mode("append").option("compression", "snappy").parquet(hdfs_path)
                            print(f"=== SAVED {hdfs_count} RECORDS TO HDFS BACKUP ===")
                        except Exception as e:
                            print(f"=== HDFS BACKUP WRITE ERROR: {e} ===")
                    
                    if minio_count > 0:
                        try:
                            current_date = expr("date_format(current_timestamp(), 'yyyy-MM-dd')").alias("partition_date")
                            minio_data_with_date = minio_data.withColumn("partition_date", current_date)
                            partition_date = minio_data_with_date.first()['partition_date']
                            minio_path = f"s3a://sensor-data/date={partition_date}"
                            minio_data_with_date.write.mode("append").option("compression", "snappy").parquet(minio_path)
                            print(f"=== SAVED {minio_count} RECORDS TO MINIO BACKUP ===")
                        except Exception as e:
                            print(f"=== MINIO BACKUP WRITE ERROR: {e} ===")
                    
                    df.unpersist()
                    
            except Exception as e:
                print(f"=== BATCH PROCESSING ERROR: {e} ===")
                traceback.print_exc()

        print("=== STARTING STREAMING QUERY ===")
        query = enriched_df.writeStream \
            .trigger(processingTime='30 seconds') \
            .foreachBatch(write_batch) \
            .option("checkpointLocation", "hdfs://namenode:9000/user/spark/checkpoint/iot-pipeline") \
            .outputMode("append") \
            .start()

        print(f"=== STREAMING QUERY STARTED WITH ID: {query.id} ===")
        return query
        
    except Exception as e:
        print(f"=== ERROR IN RUN_PIPELINE: {e} ===")
        traceback.print_exc()
        return None

def main():
    print("=== STARTING IOT PIPELINE SPARK JOB WITH ICEBERG ===")
    
    print("=== WAITING FOR SERVICES TO BE READY ===")
    time.sleep(20)
    
    spark = create_spark_session()
    if not spark:
        print("=== FAILED TO CREATE SPARK SESSION, EXITING ===")
        return
    
    if not create_hive_iceberg_table(spark):
        print("=== FAILED TO CREATE ICEBERG TABLE, CONTINUING ANYWAY ===")
    
    print("=== STARTING STREAMING PIPELINE ===")
    query = run_pipeline(spark)
    
    if query:
        try:
            print("=== PIPELINE IS RUNNING, WAITING FOR TERMINATION ===")
            query.awaitTermination()
        except KeyboardInterrupt:
            print("=== STOPPING PIPELINE ===")
            query.stop()
        except Exception as e:
            print(f"=== PIPELINE ERROR: {e} ===")
            traceback.print_exc()
            if query and query.isActive:
                query.stop()
        finally:
            if spark:
                spark.stop()
    else:
        print("=== FAILED TO START PIPELINE ===")
        if spark:
            spark.stop()

if __name__ == "__main__":
    main()
