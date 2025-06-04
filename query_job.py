#!/usr/bin/env python3

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, max as spark_max, min as spark_min, lit, when, coalesce
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, TimestampType
import traceback

def create_spark_session():
    try:
        spark = SparkSession.builder \
            .appName("DataQuery") \
            .master("spark://spark-master:7077") \
            .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1") \
            .config("spark.sql.adaptive.enabled", "false") \
            .config("spark.driver.memory", "512m") \
            .config("spark.executor.memory", "512m") \
            .config("spark.hadoop.fs.defaultFS", "hdfs://namenode:9000") \
            .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
            .config("spark.hadoop.fs.s3a.access.key", "test") \
            .config("spark.hadoop.fs.s3a.secret.key", "12345678") \
            .config("spark.hadoop.fs.s3a.path.style.access", "true") \
            .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
            .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
            .config("spark.sql.catalog.spark_catalog", "org.apache.iceberg.spark.SparkSessionCatalog") \
            .config("spark.sql.catalog.spark_catalog.type", "hive") \
            .config("spark.sql.catalog.spark_catalog.uri", "thrift://hive-metastore:9083") \
            .config("spark.sql.catalog.iceberg_catalog", "org.apache.iceberg.spark.SparkCatalog") \
            .config("spark.sql.catalog.iceberg_catalog.type", "hive") \
            .config("spark.sql.catalog.iceberg_catalog.uri", "thrift://hive-metastore:9083") \
            .config("spark.sql.catalog.iceberg_catalog.warehouse", "hdfs://namenode:9000/user/hive/warehouse") \
            .config("spark.sql.warehouse.dir", "hdfs://namenode:9000/user/hive/warehouse") \
            .config("javax.jdo.option.ConnectionURL", "jdbc:postgresql://hive-metastore-postgresql:5432/metastore") \
            .config("javax.jdo.option.ConnectionDriverName", "org.postgresql.Driver") \
            .config("javax.jdo.option.ConnectionUserName", "hive") \
            .config("javax.jdo.option.ConnectionPassword", "hive") \
            .enableHiveSupport() \
            .getOrCreate()
        
        spark.sparkContext.setLogLevel("WARN")
        print("=== SPARK SESSION WITH ICEBERG CREATED SUCCESSFULLY ===")
        return spark
    except Exception as e:
        print(f"=== FAILED TO CREATE SPARK SESSION: {e} ===")
        traceback.print_exc()
        return None

def define_unified_schema():
    return StructType([
        StructField("record_id", StringType(), True),
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
        StructField("processed_timestamp", DoubleType(), True),
        StructField("storage_location", StringType(), True),
        StructField("data_source", StringType(), True),
        StructField("kafka_timestamp", TimestampType(), True),
        StructField("partition_date", StringType(), True)
    ])

def create_unified_view_from_storage(spark):
    print("=== CREATING UNIFIED VIEW FROM STORAGE LOCATIONS ===")
    
    schema = define_unified_schema()
    unified_df = None
    
    try:
        print("=== READING FROM HDFS BACKUP ===")
        hdfs_df = spark.read.option("mergeSchema", "true").parquet("hdfs://namenode:9000/user/sensor-data/")
        hdfs_count = hdfs_df.count()
        print(f"HDFS backup: {hdfs_count} records")
        
        if hdfs_count > 0:
            hdfs_df_clean = hdfs_df.withColumn("storage_location", lit("HDFS"))
            unified_df = hdfs_df_clean
            print("Added HDFS data to unified view")
            
    except Exception as e:
        print(f"HDFS read error: {e}")
    
    try:
        print("=== READING FROM MINIO BACKUP ===")
        minio_df = spark.read.option("mergeSchema", "true").parquet("s3a://sensor-data/")
        minio_count = minio_df.count()
        print(f"MinIO backup: {minio_count} records")
        
        if minio_count > 0:
            minio_df_clean = minio_df.withColumn("storage_location", lit("MinIO"))
            
            if unified_df is not None:
                unified_df = unified_df.union(minio_df_clean)
            else:
                unified_df = minio_df_clean
            print("Added MinIO data to unified view")
            
    except Exception as e:
        print(f"MinIO read error: {e}")
    
    if unified_df is not None:
        print("=== CREATING UNIFIED TEMP VIEW ===")
        unified_df_final = unified_df.withColumn(
            "data_source",
            when(col("device_id").isNotNull(), "IoT").otherwise("API")
        ).withColumn(
            "record_id",
            coalesce(col("record_id"), lit("generated_id"))
        )
        
        unified_df_final.createOrReplaceTempView("unified_sensor_data")
        total_count = unified_df_final.count()
        print(f"=== UNIFIED VIEW CREATED WITH {total_count} TOTAL RECORDS ===")
        return unified_df_final
    else:
        print("=== NO DATA FOUND IN ANY STORAGE LOCATION ===")
        return None

def query_data():
    spark = create_spark_session()
    if not spark:
        return
    
    try:
        print("=== ATTEMPTING HIVE METASTORE CONNECTION ===")
        try:
            spark.sql("SHOW DATABASES").show()
            print("=== HIVE METASTORE CONNECTION SUCCESSFUL ===")
            metastore_available = True
        except Exception as e:
            print(f"=== HIVE METASTORE CONNECTION FAILED: {e} ===")
            metastore_available = False
        
        unified_df = None
        
        if metastore_available:
            try:
                spark.sql("SHOW TABLES IN sensor_db").show()
                df = spark.table("sensor_db.unified_sensor_data")
                record_count = df.count()
                print(f"=== FOUND {record_count} RECORDS IN HIVE TABLE ===")
                if record_count > 0:
                    unified_df = df
                    unified_df.createOrReplaceTempView("unified_sensor_data")
            except Exception as e:
                print(f"=== HIVE TABLE ACCESS FAILED: {e} ===")
        
        if unified_df is None:
            print("=== FALLING BACK TO DIRECT STORAGE ACCESS ===")
            unified_df = create_unified_view_from_storage(spark)
        
        if unified_df is not None:
            print("\n=== UNIFIED DATA SAMPLE ===")
            unified_df.show(5, truncate=False)
            
            print("\n=== FILE EXPLORER UNIFIED STRUCTURE ===")
            print("Root/")
            print("├── Unified Sensor Data/")
            
            print("\n=== DATA SOURCE DISTRIBUTION ===")
            spark.sql("""
                SELECT 
                    data_source as folder_name,
                    COUNT(*) as total_files,
                    COUNT(DISTINCT storage_location) as storage_locations,
                    MIN(partition_date) as earliest_date,
                    MAX(partition_date) as latest_date
                FROM unified_sensor_data 
                GROUP BY data_source
                ORDER BY folder_name
            """).show(truncate=False)
            
            print("\n=== VIRTUAL FILE EXPLORER HIERARCHY ===")
            spark.sql("""
                SELECT 
                    CONCAT('/', data_source) as virtual_folder,
                    COUNT(*) as file_count,
                    ROUND(AVG(CASE WHEN temperature IS NOT NULL THEN temperature END), 2) as avg_temperature,
                    ROUND(AVG(CASE WHEN humidity IS NOT NULL THEN humidity END), 2) as avg_humidity,
                    COUNT(DISTINCT storage_location) as backup_locations,
                    'Unified Storage via Iceberg/Hive' as access_method
                FROM unified_sensor_data
                GROUP BY data_source
                ORDER BY virtual_folder
            """).show(truncate=False)
            
            print("\n=== DETAILED FILE SYSTEM VIEW FOR WEB INTERFACE ===")
            spark.sql("""
                SELECT 
                    CASE 
                        WHEN data_source = 'IoT' THEN 'Device Data'
                        WHEN data_source = 'API' THEN 'Weather Station Data'
                        ELSE 'Unknown Data'
                    END as display_folder,
                    COUNT(*) as total_records,
                    COUNT(CASE WHEN device_id IS NOT NULL THEN 1 END) as iot_device_records,
                    COUNT(CASE WHEN station_uuid IS NOT NULL THEN 1 END) as weather_station_records,
                    COUNT(CASE WHEN temperature IS NOT NULL THEN 1 END) as temperature_readings,
                    COUNT(CASE WHEN humidity IS NOT NULL THEN 1 END) as humidity_readings,
                    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as geo_tagged_records,
                    COLLECT_SET(storage_location) as physical_storage_locations
                FROM unified_sensor_data
                GROUP BY data_source
                ORDER BY display_folder
            """).show(truncate=False)
            
            print("\n=== TIME-BASED FILE ORGANIZATION ===")
            spark.sql("""
                SELECT 
                    COALESCE(partition_date, SUBSTR(timestamp, 1, 10), 'unknown') as date_folder,
                    data_source as subfolder,
                    COUNT(*) as records_count,
                    MIN(timestamp) as first_record_time,
                    MAX(timestamp) as last_record_time,
                    COUNT(DISTINCT storage_location) as backup_copies
                FROM unified_sensor_data
                GROUP BY COALESCE(partition_date, SUBSTR(timestamp, 1, 10), 'unknown'), data_source
                ORDER BY date_folder DESC, subfolder
            """).show(20, truncate=False)
            
            print("\n=== STORAGE BACKEND SUMMARY ===")
            spark.sql("""
                SELECT 
                    storage_location as backend_storage,
                    COUNT(*) as record_count,
                    COUNT(DISTINCT data_source) as data_types,
                    'Accessible via unified Iceberg table' as access_note
                FROM unified_sensor_data
                GROUP BY storage_location
                ORDER BY storage_location
            """).show(truncate=False)
            
            print("\n=== UNIFIED DATA QUALITY METRICS ===")
            spark.sql("""
                SELECT 
                    'Overall Data Quality' as metric_category,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT COALESCE(device_id, station_uuid)) as unique_sources,
                    ROUND(COUNT(CASE WHEN temperature IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as temperature_coverage_pct,
                    ROUND(COUNT(CASE WHEN humidity IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as humidity_coverage_pct,
                    ROUND(COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 2) as location_coverage_pct
                FROM unified_sensor_data
            """).show(truncate=False)
            
            print("\n=== SUCCESS: UNIFIED QUERY COMPLETED ===")
            print("Data from both HDFS and MinIO successfully accessed as single unified view")
            print("File explorer structure ready for web interface implementation")
            
        else:
            print("=== ERROR: NO DATA AVAILABLE FROM ANY SOURCE ===")
        
    except Exception as e:
        print(f"=== QUERY ERROR: {e} ===")
        traceback.print_exc()
    finally:
        spark.stop()

if __name__ == "__main__":
    query_data()
