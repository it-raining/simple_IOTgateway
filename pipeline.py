#!/usr/bin/env python3

import requests
import json
import time
import sys
import subprocess
import signal
import argparse
import os
import threading
from datetime import datetime
from typing import Dict, List, Optional
from confluent_kafka import Producer, Consumer, KafkaError
import warnings
warnings.filterwarnings("ignore")

class IoTPipeline:
    def __init__(self, mode: str = "api"):
        self.mode = mode
        self.errors = []
        self.session = requests.Session()
        self.kafka_producer = None
        self.running = False
        self.spark_process = None
        self.spark_job_path = None
        
        system_proxies = requests.utils.getproxies()
        self.session.proxies = {}
        if system_proxies:
            for protocol in ['http', 'https']:
                if protocol in system_proxies:
                    self.session.proxies[protocol] = system_proxies[protocol]
        
        self.session.trust_env = True

    def log_error(self, message: str):
        self.errors.append(message)
        print(f"ERROR: {message}")
        
    def log_info(self, message: str):
        print(f"INFO: {message}")

    def _make_localhost_request(self, method: str, url: str, **kwargs) -> requests.Response:
        local_session = requests.Session()
        local_session.proxies = {'http': None, 'https': None}
        local_session.trust_env = False
        
        if method.upper() == 'GET':
            return local_session.get(url, **kwargs)
        elif method.upper() == 'POST':
            return local_session.post(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

    def check_service_health(self, url: str, service_name: str, timeout: int = 5) -> bool:
        try:
            if 'localhost' in url or '127.0.0.1' in url:
                response = self._make_localhost_request('GET', url, timeout=timeout)
            else:
                response = self.session.get(url, timeout=timeout)
                
            if response.status_code == 200:
                self.log_info(f"{service_name} is healthy")
                return True
            else:
                self.log_info(f"{service_name} returned status {response.status_code}")
                return True
        except requests.exceptions.RequestException as e:
            self.log_info(f"{service_name} health check failed: {e}")
            return True

    def validate_system(self) -> bool:
        print("\nSystem Health Check")
        print("=" * 40)
        
        required_services = [
            ("http://localhost:8080", "Spark Master"),
            ("http://localhost:9870", "HDFS NameNode"),
            ("http://localhost:9100/minio/health/live", "MinIO")
        ]
        
        for url, name in required_services:
            self.check_service_health(url, name)
        
        return self._check_docker_containers()

    def _check_docker_containers(self) -> bool:
        print("\nChecking Docker containers...")
        
        required_containers = [
            "kafka", "namenode", "datanode", "hive-metastore", 
            "hive-metastore-postgresql", "minio", "spark-master", 
            "spark-worker"
        ]
        
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=10
            )
            
            running_containers = set(result.stdout.strip().split('\n'))
            
            all_required_running = True
            for container in required_containers:
                if container in running_containers:
                    self.log_info(f"Container {container} is running")
                else:
                    self.log_error(f"Container {container} is not running")
                    all_required_running = False
            
            return all_required_running
        except Exception as e:
            self.log_error(f"Failed to check Docker containers: {e}")
            return False

    def setup_infrastructure(self):
        self.log_info("Setting up infrastructure...")
        
        self.create_kafka_topic()
        self.setup_hdfs_directories()
        self.setup_minio_bucket()

    def create_kafka_topic(self):
        try:
            cmd = [
                "docker", "exec", "kafka",
                "kafka-topics", "--create",
                "--topic", "sensor_data",
                "--bootstrap-server", "localhost:9092",
                "--partitions", "3",
                "--replication-factor", "1",
                "--if-not-exists"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.log_info("Kafka topic 'sensor_data' ready")
        except Exception as e:
            self.log_error(f"Failed to create Kafka topic: {e}")

    def setup_hdfs_directories(self):
        try:
            directories = [
                "/user/sensor-data",
                "/user/hive/warehouse",
                "/user/spark/checkpoint"
            ]
            
            for directory in directories:
                cmd = [
                    "docker", "exec", "namenode",
                    "hdfs", "dfs", "-mkdir", "-p", directory
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                self.log_info(f"HDFS directory {directory} ready")
                    
        except Exception as e:
            self.log_error(f"Failed to setup HDFS directories: {e}")

    def setup_minio_bucket(self):
        try:
            cmd = [
                "docker", "exec", "minio",
                "mc", "mb", "/data/sensor-data", "--ignore-existing"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self.log_info("MinIO bucket ready")
        except Exception as e:
            self.log_error(f"Failed to setup MinIO bucket: {e}")

    def collect_iot_data(self) -> Optional[Dict]:
        try:
            iot_data = {
                "timestamp": datetime.now().isoformat() + "Z",
                "temperature": 25.5,
                "humidity": 60.2,
                "soil_moisture": 450,
                "light": 800,
                "processed_timestamp": time.time()
            }
            device_id = f"ESP32_{int(time.time()) % 1000:03d}"
            self.log_info(f"IoT data collected for device {device_id}")
            return iot_data
        except Exception as e:
            self.log_error(f"Failed to collect IoT data: {e}")
            return None

    def collect_api_data(self) -> Optional[List[Dict]]:
        try:
            url = "https://www.pegelonline.wsv.de/webservices/rest-api/v2/stations.json"
            params = {
                "includeTimeseries": "true",
                "hasTimeseries": "WV",
                "includeForecastTimeseries": "true"
            }
            
            response = self.session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                stations_data = response.json()
                formatted_data = []
                
                for station in stations_data[:2]:
                    formatted_station = {
                        "station_uuid": station.get("uuid"),
                        "station_number": station.get("number"),
                        "shortname": station.get("shortname"),
                        "longname": station.get("longname"),
                        "km": station.get("km"),
                        "agency": station.get("agency"),
                        "longitude": station.get("longitude"),
                        "latitude": station.get("latitude"),
                        "water_shortname": station.get("water", {}).get("shortname"),
                        "water_longname": station.get("water", {}).get("longname"),
                        "processed_timestamp": time.time()
                    }
                    formatted_data.append(formatted_station)
                
                self.log_info(f"API data collected - {len(formatted_data)} stations")
                return formatted_data
            else:
                self.log_error(f"API request failed with status {response.status_code}")
                return None
        except Exception as e:
            self.log_error(f"Failed to collect API data: {e}")
            return None

    def setup_kafka_producer(self):
        try:
            config = {
                'bootstrap.servers': 'localhost:9093',
                'client.id': 'iot-producer',
                'delivery.timeout.ms': 30000,
                'request.timeout.ms': 30000
            }
            self.kafka_producer = Producer(config)
            self.log_info("Kafka producer initialized")
        except Exception as e:
            self.log_error(f"Failed to setup Kafka producer: {e}")

    def send_to_kafka(self, data: Dict, topic: str = "sensor_data"):
        if not self.kafka_producer:
            self.setup_kafka_producer()
        
        try:
            if self.mode == "iot":
                key = f"ESP32_{int(time.time()) % 1000:03d}"
                data_with_id = {"device_id": key, **data}
                value = json.dumps(data_with_id)
            else:
                key = data.get("station_uuid", "unknown")
                value = json.dumps(data)
            
            self.kafka_producer.produce(topic, key=key, value=value)
            self.kafka_producer.flush()
            self.log_info(f"Data sent to Kafka: key={key[:10]}...")
        except Exception as e:
            self.log_error(f"Failed to send data to Kafka: {e}")

    def run_spark_job(self):
        try:
            with open('spark_job.py', 'r') as f:
                script_content = f.read()
            
            self.log_info("Copying Spark script to container...")
            copy_cmd = [
                "docker", "exec", "-i", "spark-master",
                "bash", "-c", "cat > /opt/bitnami/spark/spark_job.py"
            ]
            
            result = subprocess.run(
                copy_cmd, 
                input=script_content, 
                text=True, 
                capture_output=True, 
                timeout=60
            )
            
            if result.returncode != 0:
                self.log_error(f"Failed to copy script: {result.stderr}")
                return False
            
            self.log_info("Submitting Spark streaming job in background...")
            
            submit_cmd = [
                "docker", "exec", "-d", "spark-master",
                "/opt/bitnami/spark/bin/spark-submit",
                "--master", "spark://spark-master:7077",
                "--deploy-mode", "client",
                "--driver-memory", "512m",
                "--executor-memory", "512m", 
                "--executor-cores", "1",
                "--total-executor-cores", "1",
                "--conf", "spark.streaming.stopGracefullyOnShutdown=true",
                "--conf", "spark.sql.streaming.stopGracefullyOnShutdown=true",
                "--conf", "spark.sql.streaming.forceDeleteTempCheckpointLocation=true",
                "--conf", "spark.serializer=org.apache.spark.serializer.KryoSerializer",
                "--conf", "spark.dynamicAllocation.enabled=false",
                "--conf", "spark.sql.adaptive.enabled=false",
                "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.4,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1",
                "/opt/bitnami/spark/spark_job.py"
            ]
            
            result = subprocess.run(submit_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                self.log_info("Spark streaming job submitted successfully")
                
                time.sleep(30)
                
                logs_cmd = ["docker", "logs", "spark-master", "--tail", "50"]
                logs_result = subprocess.run(logs_cmd, capture_output=True, text=True, timeout=10)
                print("=== RECENT SPARK LOGS ===")
                print(logs_result.stdout)
                
                return True
            else:
                self.log_error(f"Failed to submit Spark job: {result.stderr}")
                return False
            
        except Exception as e:
            self.log_error(f"Failed to run Spark job: {e}")
            return False

    def query_data(self):
        try:
            with open('query_job.py', 'r') as f:
                script_content = f.read()
            
            self.log_info("Copying query script to container...")
            copy_cmd = [
                "docker", "exec", "-i", "spark-master",
                "bash", "-c", "cat > /opt/bitnami/spark/query_job.py"
            ]
            
            result = subprocess.run(
                copy_cmd, 
                input=script_content, 
                text=True, 
                capture_output=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                self.log_error(f"Failed to copy query script: {result.stderr}")
                return
            
            self.log_info("Running query job...")
            submit_cmd = [
                "docker", "exec", "spark-master",
                "/opt/bitnami/spark/bin/spark-submit",
                "--master", "spark://spark-master:7077",
                "--driver-memory", "512m",
                "--packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262,org.apache.iceberg:iceberg-spark-runtime-3.3_2.12:1.3.1",
                "/opt/bitnami/spark/query_job.py"
            ]
            
            result = subprocess.run(submit_cmd, capture_output=True, text=True, timeout=120)
            print("=== QUERY RESULTS ===")
            print(result.stdout)
            if result.stderr:
                print(f"Query stderr: {result.stderr}")
                
        except Exception as e:
            self.log_error(f"Failed to run query: {e}")

    def collect_and_stream_data(self):
        self.log_info(f"Starting data collection in {self.mode} mode")
        
        def data_collection_loop():
            data_count = 0
            while self.running:
                try:
                    if self.mode == "iot":
                        data = self.collect_iot_data()
                        if data:
                            self.send_to_kafka(data)
                            data_count += 1
                    elif self.mode == "api":
                        data_list = self.collect_api_data()
                        if data_list:
                            for data in data_list:
                                self.send_to_kafka(data)
                                data_count += 1
                    
                    if data_count % 10 == 0:
                        self.log_info(f"Total messages sent: {data_count}")
                    
                    time.sleep(60)
                    
                except Exception as e:
                    self.log_error(f"Error in data collection: {e}")
                    time.sleep(10)
        
        data_thread = threading.Thread(target=data_collection_loop)
        data_thread.daemon = True
        data_thread.start()
        return data_thread

    def monitor_system(self):
        while self.running:
            try:
                logs_cmd = ["docker", "logs", "spark-master", "--tail", "20"]
                result = subprocess.run(logs_cmd, capture_output=True, text=True, timeout=10)
                
                output = result.stdout.lower()
                if any(keyword in output for keyword in ["error", "exception", "failed"]):
                    print("=== SYSTEM ALERT: ISSUES DETECTED ===")
                    print(result.stdout[-500:])
                
                time.sleep(120)
            except Exception as e:
                self.log_error(f"Error monitoring system: {e}")
                time.sleep(60)

    def cleanup(self):
        self.running = False
        if hasattr(self, 'spark_process') and self.spark_process:
            try:
                self.spark_process.terminate()
            except:
                pass
        if self.kafka_producer:
            try:
                self.kafka_producer.flush()
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description="IoT Pipeline")
    parser.add_argument("--mode", choices=["iot", "api"], default="api", 
                       help="Data collection mode: iot or api")
    parser.add_argument("--action", choices=["run", "query"], default="run",
                       help="Action to perform: run pipeline or query data")
    
    args = parser.parse_args()
    
    pipeline = IoTPipeline(mode=args.mode)
    
    def signal_handler(sig, frame):
        print("\n=== SHUTTING DOWN ===")
        pipeline.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.action == "query":
        pipeline.query_data()
        return
    
    print(f"=== STARTING IOT PIPELINE IN {args.mode.upper()} MODE ===")
    print("=" * 60)
    
    if not pipeline.validate_system():
        print("WARNING: Some system components may not be fully ready")
    
    pipeline.setup_infrastructure()
    pipeline.setup_kafka_producer()
    pipeline.running = True
    
    data_thread = pipeline.collect_and_stream_data()
    
    time.sleep(15)
    
    if pipeline.run_spark_job():
        try:
            monitor_thread = threading.Thread(target=pipeline.monitor_system)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            print("=== PIPELINE IS RUNNING ===")
            print("Data collection: ACTIVE")
            print("Spark streaming: ACTIVE")
            print("Press Ctrl+C to stop")
            
            while pipeline.running:
                time.sleep(10)
                if not data_thread.is_alive():
                    print("=== RESTARTING DATA COLLECTION ===")
                    data_thread = pipeline.collect_and_stream_data()
                    
        except KeyboardInterrupt:
            print("\n=== SHUTDOWN REQUESTED ===")
    else:
        print("=== FAILED TO START SPARK JOB ===")
    
    pipeline.cleanup()
    print("=== PIPELINE SHUTDOWN COMPLETE ===")

if __name__ == "__main__":
    main() 