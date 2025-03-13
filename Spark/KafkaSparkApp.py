from pyspark.sql import SparkSession
from pyspark.sql.functions import col, unbase64, from_json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

def main():
    # Khởi tạo SparkSession với master là local[*]
    spark = SparkSession.builder \
        .appName("KafkaSparkBase64Decode") \
        .master("local[*]") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # # Cấu hình cho MinIO (giả sử MinIO chạy trên host minio-server, port 9000)
    # spark.conf.set("spark.hadoop.fs.s3a.endpoint", "http://minio-server:9000")
    # spark.conf.set("spark.hadoop.fs.s3a.access.key", "<your-access-key>")
    # spark.conf.set("spark.hadoop.fs.s3a.secret.key", "<your-secret-key>")
    # spark.conf.set("spark.hadoop.fs.s3a.path.style.access", "true")
    # Các cấu hình khác nếu cần, ví dụ: spark.hadoop.fs.s3a.impl

    # Cấu hình Kafka: thay đổi kafka_bootstrap_servers nếu cần
    kafka_bootstrap_servers = "kafk-1:9094,kafk-2:9094,kafk-3:9094"
    topic = "esp32_data"  # Thay thế nếu cần

    # Đọc dữ liệu stream từ Kafka, key và value được đọc ở dạng binary
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
        .option("subscribe", topic) \
        .option("startingOffsets", "latest") \
        .load()

    # Giữ lại cột "value" và chuyển đổi key sang string
    kafka_df = kafka_df.selectExpr("CAST(key AS STRING) as key", "CAST(value AS STRING) as value", "timestamp")

    # Sử dụng unbase64 để giải mã cột "value" (giả sử dữ liệu được mã hóa base64)
    decoded_df = kafka_df.withColumn("decoded_value", unbase64(col("value")).cast("string")) \
                         .select("key", "decoded_value", "timestamp")

    # Định nghĩa schema cho JSON (các trường có thể thay đổi tùy dữ liệu của bạn)
    json_schema = StructType([
        StructField("timestamp", TimestampType()),
        StructField("temperature", IntegerType()),
        StructField("humidity", IntegerType()),
        StructField("soil_moisture", IntegerType()),
        StructField("light", IntegerType())
    ])

    # Parse chuỗi JSON thành DataFrame có cấu trúc theo schema
    json_parsed_df = decoded_df.withColumn("json_data", from_json(col("decoded_value"), json_schema)) \
                                .select("key", "timestamp", "json_data.*")

    # # Việc ghi dữ liệu ra HDFS dưới dạng file Parquet
    # hdfsQuery = json_parsed_df.writeStream \
    #     .format("parquet") \
    #     .option("path", "hdfs://namenode:8020/data/sensor/") \
    #     .option("checkpointLocation", "/tmp/checkpoint/hdfs") \
    #     .trigger(processingTime="10 seconds") \
    #     .start()

    # # Việc ghi dữ liệu ra MinIO (sử dụng giao thức s3a) dưới dạng file Parquet
    # minioQuery = json_parsed_df.writeStream \
    #     .format("parquet") \
    #     .option("path", "s3a://mybucket/sensor_data/") \
    #     .option("checkpointLocation", "/tmp/checkpoint/minio") \
    #     .trigger(processingTime="10 seconds") \
    #     .start()

    # Ghi kết quả ra console để kiểm tra (tùy chọn, không cần thiết nếu ghi ra sink đã đủ)
    consoleQuery = json_parsed_df.writeStream \
        .format("console") \
        .option("truncate", "false") \
        .trigger(processingTime="10 seconds") \
        .start()

    # Đợi tất cả query kết thúc
    # hdfsQuery.awaitTermination()
    # minioQuery.awaitTermination()
    consoleQuery.awaitTermination()

if __name__ == "__main__":
    main()
