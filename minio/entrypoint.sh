#!/bin/bash
echo "Starting MinIO..."
echo "MinIO URL: ${MINIO_URL}"
echo "MinIO Root User: ${MINIO_ROOT_USER}" 
echo "MinIO Root Password: ${MINIO_ROOT_PASSWORD}"
echo "MinIO Alias: ${MINIO_ALIAS}"

/usr/bin/mc config host add ${MINIO_ALIAS} ${MINIO_URL} ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

/usr/bin/mc mb ${MINIO_ALIAS}/minio
/usr/bin/mc policy download ${MINIO_ALIAS}/minio

exit 0
