# --- Stage 0: Downloader ---
  FROM quay.io/curl/curl-base:latest as downloader
  # Sử dụng thư mục làm việc /tmp/jars để lưu các file JAR
  WORKDIR /tmp/jars
  # Tải các dependency cần thiết cho Spark 3.5.5 và Iceberg
  RUN curl -sSL "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.819/aws-java-sdk-bundle-1.11.819.jar" \
        --output aws-java-sdk-bundle-1.11.819.jar && \
      curl -sSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.1/hadoop-aws-3.3.1.jar" \
        --output hadoop-aws-3.3.1.jar && \
      # Các dependency phụ trợ
      curl -sSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.2.20/postgresql-42.2.20.jar" \
        --output postgresql-42.2.20.jar && \
      curl -sSL "https://repo1.maven.org/maven2/net/java/dev/jets3t/jets3t/0.9.4/jets3t-0.9.4.jar" \
        --output jets3t-0.9.4.jar && \
      # Apache Iceberg dependencies (phiên bản 1.2.0)
      curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark3-runtime_2.12/1.2.0/iceberg-spark3-runtime_2.12-1.2.0.jar" \
        --output iceberg-spark3-runtime_2.12-1.2.0.jar && \
      curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-core/1.2.0/iceberg-core-1.2.0.jar" \
        --output iceberg-core-1.2.0.jar && \
      curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-api/1.2.0/iceberg-api-1.2.0.jar" \
        --output iceberg-api-1.2.0.jar && \
      curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-hive-metastore/1.2.0/iceberg-hive-metastore-1.2.0.jar" \
        --output iceberg-hive-metastore-1.2.0.jar
  
  # --- Stage 1: Final Image ---
  FROM bitnami/spark:latest
  # Định nghĩa SPARK_HOME cho image cuối
  ENV SPARK_HOME=/opt/bitnami/spark
  ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
  ENV PYSPARK_PYTHON=/opt/bitnami/python/bin/python3
  
  USER root
  
  # Cài đặt các gói hệ thống cần thiết và pip (nếu chưa có)
  RUN install_packages python3-pip wget procps software-properties-common libpq-dev
  
  # Cài đặt các package Python cần thiết
  RUN pip install --no-cache-dir psycopg2-binary kafka-python requests confluent-kafka
  
  # Cài đặt MinIO client (mc) để giao tiếp với MinIO
  RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc && \
      chmod +x /usr/local/bin/mc
  
  # Copy các file JAR đã tải từ stage downloader vào thư mục jars của Spark
  # (Lưu ý: thư mục SPARK_HOME/jars đã có sẵn trong image Bitnami Spark)
  COPY --from=downloader /tmp/jars/ $SPARK_HOME/jars/
  
  # COPY file cấu hình Hive (ví dụ: hive-site.xml) vào thư mục conf của Spark
  WORKDIR $SPARK_HOME
  COPY hive-site.xml conf/hive-site.xml
  
  # --- Cài đặt Hive ---
  ARG HIVE_VERSION
  ENV HIVE_VERSION=${HIVE_VERSION:-3.1.2}
  ENV HIVE_HOME=/opt/hive
  ENV PATH=$HIVE_HOME/bin:$PATH
  WORKDIR /opt
  RUN apt-get update && \
      apt-get install -y wget procps software-properties-common && \
      wget https://archive.apache.org/dist/hive/hive-$HIVE_VERSION/apache-hive-$HIVE_VERSION-bin.tar.gz && \
      tar -xzvf apache-hive-$HIVE_VERSION-bin.tar.gz && \
      rm -rf $HIVE_HOME && \
      mv apache-hive-$HIVE_VERSION-bin $HIVE_HOME && \
      wget https://jdbc.postgresql.org/download/postgresql-9.4.1212.jar -O $HIVE_HOME/lib/postgresql-jdbc.jar && \
      rm apache-hive-$HIVE_VERSION-bin.tar.gz && \
      rm -rf /var/lib/apt/lists/*
  
  # Thay thế các jar Hive (và Calcite) trong Spark bằng các jar từ Hive để đảm bảo tương thích
  RUN rm -f $SPARK_HOME/jars/hive-* && \
      cp $HIVE_HOME/lib/hive-* $SPARK_HOME/jars/ && \
      cp $HIVE_HOME/lib/calcite-* $SPARK_HOME/jars/ && \
      rm -rf $HIVE_HOME
  
  # --- Cấu hình Spark ---
  # Cập nhật spark-defaults.conf để bật Iceberg (Iceberg sử dụng Hive Metastore, warehouse trên HDFS)
  RUN echo 'spark.sql.catalog.iceberg org.apache.iceberg.spark.SparkCatalog' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
      echo 'spark.sql.catalog.iceberg.type=hive' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
      echo 'spark.sql.catalog.iceberg.warehouse=hdfs://namenode:9000/user/hive/warehouse' >> "$SPARK_HOME/conf/spark-defaults.conf"
  
  # Thiết lập working directory (sử dụng HOME của user mặc định)
  WORKDIR "${HOME}"
  # Chuyển sang user non-root (theo biến môi trường NB_UID đã định nghĩa trong image Bitnami Spark)
  USER ${NB_UID}
  