# --- Stage 0: Downloader ---
FROM quay.io/curl/curl-base:latest as downloader

# Tải các dependency cần thiết cho Spark 3.5.5 và Iceberg
RUN curl -sSL "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.819/aws-java-sdk-bundle-1.11.819.jar" \
      --output /tmp/aws-java-sdk-bundle-1.11.819.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.8.0/commons-pool2-2.8.0.jar" \
      --output /tmp/commons-pool2-2.8.0.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.1/hadoop-aws-3.3.1.jar" \
      --output /tmp/hadoop-aws-3.3.1.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/2.8.1/kafka-clients-2.8.1.jar" \
      --output /tmp/kafka-clients-2.8.1.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/spark/spark-sql_2.12/3.5.5/spark-sql_2.12-3.5.5.jar" \
      --output /tmp/spark-sql_2.12-3.5.5.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.5/spark-sql-kafka-0-10_2.12-3.5.5.jar" \
      --output /tmp/spark-sql-kafka-0-10_2.12-3.5.5.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/spark/spark-tags_2.12/3.5.5/spark-tags_2.12-3.5.5.jar" \
      --output /tmp/spark-tags_2.12-3.5.5.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.5/spark-token-provider-kafka-0-10_2.12-3.5.5.jar" \
      --output /tmp/spark-token-provider-kafka-0-10_2.12-3.5.5.jar && \
    # Các dependency phụ trợ
    curl -sSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.2.20/postgresql-42.2.20.jar" \
      --output /tmp/postgresql-42.2.20.jar && \
    curl -sSL "https://repo1.maven.org/maven2/com/google/guava/guava/27.0-jre/guava-27.0-jre.jar" \
      --output /tmp/guava-27.0-jre.jar && \
    curl -sSL "https://repo1.maven.org/maven2/net/java/dev/jets3t/jets3t/0.9.4/jets3t-0.9.4.jar" \
      --output /tmp/jets3t-0.9.4.jar && \
    curl -sSL "https://repo1.maven.org/maven2/io/delta/delta-core_2.12/1.0.0/delta-core_2.12-1.0.0.jar" \
      --output /tmp/delta-core_2.12-1.0.0.jar && \
    # Apache Iceberg dependencies (phiên bản 1.2.0)
    curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark3-runtime_2.12/1.2.0/iceberg-spark3-runtime_2.12-1.2.0.jar" \
      --output /tmp/iceberg-spark3-runtime_2.12-1.2.0.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-core/1.2.0/iceberg-core-1.2.0.jar" \
      --output /tmp/iceberg-core-1.2.0.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-api/1.2.0/iceberg-api-1.2.0.jar" \
      --output /tmp/iceberg-api-1.2.0.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-hive-metastore/1.2.0/iceberg-hive-metastore-1.2.0.jar" \
      --output /tmp/iceberg-hive-metastore-1.2.0.jar

# --- Stage 1: Final Image ---
FROM bitnami/spark:latest

USER root

# Cài đặt các gói hệ thống cần thiết và pip (nếu chưa có)
RUN install_packages python3-pip wget procps software-properties-common libpq-dev

# Cài đặt Jupyter Notebook/Lab và các package Python cần thiết (sử dụng psycopg2-binary)
RUN pip install --no-cache-dir jupyterlab notebook delta-spark psycopg2-binary

# Cài đặt MinIO client (mc) để giao tiếp với MinIO
RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc

# Thiết lập các biến môi trường cho Spark
ENV SPARK_HOME=/opt/bitnami/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYSPARK_PYTHON=/opt/bitnami/python/bin/python3

# --- Cập nhật dependency cho Spark 3.5.5 ---
# Xóa các jar cũ không cần thiết (ví dụ: guava-14.0.1.jar) và các jar trùng tên
RUN rm -f $SPARK_HOME/jars/guava-14.0.1.jar && \
    rm -f $SPARK_HOME/jars/aws-java-sdk-bundle-*.jar && \
    rm -f $SPARK_HOME/jars/commons-pool2-*.jar && \
    rm -f $SPARK_HOME/jars/hadoop-aws-*.jar && \
    rm -f $SPARK_HOME/jars/kafka-clients-*.jar && \
    rm -f $SPARK_HOME/jars/spark-sql_2.12-*.jar && \
    rm -f $SPARK_HOME/jars/spark-sql-kafka-0-10_2.12-*.jar && \
    rm -f $SPARK_HOME/jars/spark-tags_2.12-*.jar && \
    rm -f $SPARK_HOME/jars/spark-token-provider-kafka-0-10_2.12-*.jar

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

# Thay thế các jar Hive (và Calcite) trong Spark bằng các jar từ Hive vừa cài đặt
RUN rm -f $SPARK_HOME/jars/hive-* && \
    cp $HIVE_HOME/lib/hive-* $SPARK_HOME/jars/ && \
    cp $HIVE_HOME/lib/calcite-* $SPARK_HOME/jars/ && \
    rm -rf $HIVE_HOME

# --- Cài đặt các dependency bổ sung cho Spark (S3, Kafka, Delta, Iceberg) ---
# COPY các file jar đã tải từ stage downloader vào thư mục jars của Spark
COPY --from=downloader /tmp/aws-java-sdk-bundle-1.11.819.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/commons-pool2-2.8.0.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/hadoop-aws-3.3.1.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/kafka-clients-2.8.1.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/spark-sql_2.12-3.5.5.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/spark-sql-kafka-0-10_2.12-3.5.5.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/spark-tags_2.12-3.5.5.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/spark-token-provider-kafka-0-10_2.12-3.5.5.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/postgresql-42.2.20.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/guava-27.0-jre.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/jets3t-0.9.4.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/delta-core_2.12-1.0.0.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/iceberg-spark3-runtime_2.12-1.2.0.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/iceberg-core-1.2.0.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/iceberg-api-1.2.0.jar $SPARK_HOME/jars/
COPY --from=downloader /tmp/iceberg-hive-metastore-1.2.0.jar $SPARK_HOME/jars/

# --- Cấu hình Spark ---
RUN echo 'spark.sql.extensions io.delta.sql.DeltaSparkSessionExtension' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
    echo 'spark.sql.catalog.spark_catalog org.apache.spark.sql.delta.catalog.DeltaCatalog' >> "$SPARK_HOME/conf/spark-defaults.conf"

# Thiết lập working directory (sử dụng HOME của user mặc định)
WORKDIR "${HOME}"

# Chuyển sang user non-root (theo biến môi trường NB_UID được định nghĩa trong image Bitnami Spark)
USER ${NB_UID}

# CMD khởi chạy JupyterLab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--NotebookApp.token=''", "--allow-root"]