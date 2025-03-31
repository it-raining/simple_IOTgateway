# Stage 0: Downloader – tải các file jar cần thiết
FROM quay.io/curl/curl-base:latest as downloader

RUN curl -sSL "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.819/aws-java-sdk-bundle-1.11.819.jar" --output /tmp/aws-java-sdk-bundle-1.11.819.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.1/hadoop-aws-3.3.1.jar" --output /tmp/hadoop-aws-3.3.1.jar && \
    curl -sSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/42.2.20/postgresql-42.2.20.jar" --output /tmp/postgresql-42.2.20.jar && \
    curl -sSL "https://repo1.maven.org/maven2/net/java/dev/jets3t/jets3t/0.9.4/jets3t-0.9.4.jar" --output /tmp/jets3t-0.9.4.jar && \
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
    pip install --no-cache-dir jupyterlab notebook psycopg2-binary

# Cài đặt MinIO client (mc) để giao tiếp với MinIO
RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc

# Tạo user jovyan (theo convention của image Jupyter) và thư mục làm việc
RUN useradd -m jovyan && mkdir -p /home/jovyan/work && chown -R jovyan:jovyan /home/jovyan

# Thiết lập các biến môi trường cho Spark
ENV SPARK_HOME=/opt/bitnami/spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYSPARK_PYTHON=/opt/bitnami/python/bin/python3

# --- Cập nhật dependency cho Spark 3.5.5 ---
# Xóa các jar không cần thiết
RUN rm -f $SPARK_HOME/jars/aws-java-sdk-bundle-*.jar && \
    rm -f $SPARK_HOME/jars/hadoop-aws-*.jar && \

# Copy toàn bộ file jar đã tải từ stage downloader vào thư mục tạm /tmp/downloader trong image hiện tại
COPY --from=downloader /tmp/ /tmp/downloader/

# Trong bước này, với mỗi dependency, nếu trong $SPARK_HOME/jars đã có file với tên cơ bản tương ứng, thì bỏ qua; nếu chưa có, thì copy file từ /tmp/downloader
RUN if ls $SPARK_HOME/jars/aws-java-sdk-bundle-*.jar 2>/dev/null | grep -qi "aws-java-sdk-bundle"; then \
         echo "aws-java-sdk-bundle đã tồn tại, bỏ qua"; \
       else \
         cp /tmp/downloader/aws-java-sdk-bundle-1.11.819.jar $SPARK_HOME/jars/; \
       fi && \
    if ls $SPARK_HOME/jars/hadoop-aws-*.jar 2>/dev/null | grep -qi "hadoop-aws"; then \
         echo "hadoop-aws đã tồn tại, bỏ qua"; \
       else \
         cp /tmp/downloader/hadoop-aws-3.3.1.jar $SPARK_HOME/jars/; \
       fi && \
    if ls $SPARK_HOME/jars/postgresql-*.jar 2>/dev/null | grep -qi "postgresql"; then \
         echo "postgresql jar đã tồn tại, bỏ qua"; \
       else \
         cp /tmp/downloader/postgresql-42.2.20.jar $SPARK_HOME/jars/; \
       fi && \
    if ls $SPARK_HOME/jars/jets3t-*.jar 2>/dev/null | grep -qi "jets3t"; then \
         echo "jets3t jar đã tồn tại, bỏ qua"; \
       else \
         cp /tmp/downloader/jets3t-0.9.4.jar $SPARK_HOME/jars/; \
       fi && \
    if ls $SPARK_HOME/jars/iceberg-spark3-runtime_2.12-*.jar 2>/dev/null | grep -qi "iceberg-spark3-runtime_2.12"; then \
         echo "iceberg-spark3-runtime đã tồn tại, bỏ qua"; \
       else \
         cp /tmp/downloader/iceberg-spark3-runtime_2.12-1.2.0.jar $SPARK_HOME/jars/; \
       fi && \
    if ls $SPARK_HOME/jars/iceberg-core-*.jar 2>/dev/null | grep -qi "iceberg-core"; then \
         echo "iceberg-core đã tồn tại, bỏ qua"; \
       else \
         cp /tmp/downloader/iceberg-core-1.2.0.jar $SPARK_HOME/jars/; \
       fi && \
    if ls $SPARK_HOME/jars/iceberg-api-*.jar 2>/dev/null | grep -qi "iceberg-api"; then \
         echo "iceberg-api đã tồn tại, bỏ qua"; \
       else \
         cp /tmp/downloader/iceberg-api-1.2.0.jar $SPARK_HOME/jars/; \
       fi && \
    if ls $SPARK_HOME/jars/iceberg-hive-metastore-*.jar 2>/dev/null | grep -qi "iceberg-hive-metastore"; then \
         echo "iceberg-hive-metastore đã tồn tại, bỏ qua"; \
       else \
         cp /tmp/downloader/iceberg-hive-metastore-1.2.0.jar $SPARK_HOME/jars/; \
       fi && \
    rm -rf /tmp/downloader

# Copy file cấu hình hive-site.xml vào thư mục conf của Spark
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
# Cập nhật spark-defaults.conf để bật và Iceberg (Iceberg sử dụng Hive Metastore, warehouse trên HDFS)
RUN echo 'spark.sql.catalog.iceberg org.apache.iceberg.spark.SparkCatalog' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
    echo 'spark.sql.catalog.iceberg.type=hive' >> "$SPARK_HOME/conf/spark-defaults.conf" && \
    echo 'spark.sql.catalog.iceberg.warehouse=hdfs://namenode:8020/user/hive/warehouse' >> "$SPARK_HOME/conf/spark-defaults.conf"

# Thiết lập thư mục làm việc cho user jovyan và chuyển sang user này
WORKDIR /home/jovyan
USER jovyan

# CMD khởi chạy JupyterLab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--NotebookApp.token=''"]
