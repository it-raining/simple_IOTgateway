# Stage 0: Downloader – tải các file jar cần thiết
FROM quay.io/curl/curl-base:latest as downloader

RUN curl -sSL "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.819/aws-java-sdk-bundle-1.11.819.jar" --output /tmp/aws-java-sdk-bundle-1.11.819.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.8.0/commons-pool2-2.8.0.jar" --output /tmp/commons-pool2-2.8.0.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.1/hadoop-aws-3.3.1.jar" --output /tmp/hadoop-aws-3.3.1.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/2.8.1/kafka-clients-2.8.1.jar" --output /tmp/kafka-clients-2.8.1.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/spark/spark-sql_2.12/3.5.5/spark-sql_2.12-3.5.5.jar" --output /tmp/spark-sql_2.12-3.5.5.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.5/spark-sql-kafka-0-10_2.12-3.5.5.jar" --output /tmp/spark-sql-kafka-0-10_2.12-3.5.5.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/spark/spark-tags_2.12/3.5.5/spark-tags_2.12-3.5.5.jar" --output /tmp/spark-tags_2.12-3.5.5.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.5/spark-token-provider-kafka-0-10_2.12-3.5.5.jar" --output /tmp/spark-token-provider-kafka-0-10_2.12-3.5.5.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.2.20/postgresql-42.2.20.jar" --output /tmp/postgresql-42.2.20.jar && \
    curl -sSL "https://repo1.maven.org/maven2/com/google/guava/guava/27.0-jre/guava-27.0-jre.jar" --output /tmp/guava-27.0-jre.jar && \
    curl -sSL "https://repo1.maven.org/maven2/net/java/dev/jets3t/jets3t/0.9.4/jets3t-0.9.4.jar" --output /tmp/jets3t-0.9.4.jar && \
    curl -sSL "https://repo1.maven.org/maven2/io/delta/delta-core_2.12/1.0.0/delta-core_2.12-1.0.0.jar" --output /tmp/delta-core_2.12-1.0.0.jar && \
    # Apache Iceberg dependencies
    curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark3-runtime_2.12/1.2.0/iceberg-spark3-runtime_2.12-1.2.0.jar" --output /tmp/iceberg-spark3-runtime_2.12-1.2.0.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-core/1.2.0/iceberg-core-1.2.0.jar" --output /tmp/iceberg-core-1.2.0.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-api/1.2.0/iceberg-api-1.2.0.jar" --output /tmp/iceberg-api-1.2.0.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-hive-metastore/1.2.0/iceberg-hive-metastore-1.2.0.jar" --output /tmp/iceberg-hive-metastore-1.2.0.jar

# Stage 1: Final image dựa trên Bitnami Spark (phiên bản 3.5.5) và cài đặt Jupyter, Hive, …
FROM bitnami/spark:latest

USER root

# Cài đặt Jupyter Notebook và các gói Python cần thiết
RUN install_packages python3-pip && \
    pip install --no-cache-dir jupyterlab notebook delta-spark psycopg2

# Tạo user jovyan (theo convention của image Jupyter) và thư mục làm việc
RUN useradd -m jovyan && mkdir -p /home/jovyan/work && chown -R jovyan:jovyan /home/jovyan

# Thiết lập các biến môi trường cho Spark
ENV SPARK_HOME=/opt/bitnami/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYSPARK_PYTHON=/opt/bitnami/python/bin/python3

# --- Cập nhật dependency cho Spark 3.5.5 ---
# Xóa các jar không cần thiết
RUN rm -f $SPARK_HOME/jars/guava-14.0.1.jar && \
    rm -f $SPARK_HOME/jars/aws-java-sdk-bundle-*.jar && \
    rm -f $SPARK_HOME/jars/commons-pool2-*.jar && \
    rm -f $SPARK_HOME/jars/hadoop-aws-*.jar && \
    rm -f $SPARK_HOME/jars/kafka-clients-*.jar && \
    rm -f $SPARK_HOME/jars/spark-sql_2.12-*.jar && \
    rm -f $SPARK_HOME/jars/spark-sql-kafka-0-10_2.12-*.jar && \
    rm -f $SPARK_HOME/jars/spark-tags_2.12-*.jar && \
    rm -f $SPARK_HOME/jars/spark-token-provider-kafka-0-10_2.12-*.jar

# Copy các file jar đã tải từ stage downloader vào thư mục jars của Spark
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

# Copy file cấu hình hive-site.xml vào thư mục conf của Spark
WORKDIR $SPARK_HOME
COPY hive-site.xml conf/hive-site.xml

# --- Cài đặt Hive ---
ARG HIVE_VERSION
ENV HIVE_VERSION=${HIVE_VERSION:-3.1.2}
ENV HIVE_HOME=/opt/hive
ENV PATH=$HIVE_HOME/bin:$PATH
WORKDIR /opt
RUN apt update && apt install -y wget procps software-properties-common && \
    wget https://archive.apache.org/dist/hive/hive-$HIVE_VERSION/apache-hive-$HIVE_VERSION-bin.tar.gz && \
    tar -xzvf apache-hive-$HIVE_VERSION-bin.tar.gz && \
    mv apache-hive-$HIVE_VERSION-bin hive && \
    rm apache-hive-$HIVE_VERSION-bin.tar.gz && \
    apt autoremove --purge wget -y && \
    rm -rf /var/lib/apt/lists/*

# (Nếu cần) Cài đặt OpenJDK 8 – tuy nhiên Bitnami Spark đã đi kèm JDK
RUN apt update && \
    apt autoremove --purge openjdk* -y && \
    apt install -y openjdk-8-jdk

# Thay thế các jar Hive (và Calcite) trong Spark bằng các jar từ Hive để đảm bảo tương thích
RUN rm -f $SPARK_HOME/jars/hive-* && \
    cp $HIVE_HOME/lib/hive-* $SPARK_HOME/jars/ && \
    cp $HIVE_HOME/lib/calcite-* $SPARK_HOME/jars/ && \
    rm -rf $HIVE_HOME

# --- Cấu hình Spark ---
# Cập nhật spark-defaults.conf để bật Delta và Iceberg (Iceberg sử dụng Hive Metastore, warehouse trên HDFS)
RUN echo 'spark.sql.extensions io.delta.sql.DeltaSparkSessionExtension,org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
    echo 'spark.sql.catalog.spark_catalog org.apache.spark.sql.delta.catalog.DeltaCatalog' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
    echo 'spark.sql.catalog.iceberg org.apache.iceberg.spark.SparkCatalog' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
    echo 'spark.sql.catalog.iceberg.type=hive' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
    echo 'spark.sql.catalog.iceberg.warehouse=hdfs://namenode:8020/user/hive/warehouse' >> "$SPARK_HOME/conf/spark-defaults.conf"

# Thiết lập thư mục làm việc cho user jovyan và chuyển sang user này
WORKDIR /home/jovyan
USER jovyan

# CMD khởi chạy JupyterLab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--NotebookApp.token=''"]
