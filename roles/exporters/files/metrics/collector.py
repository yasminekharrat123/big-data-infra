from datetime import datetime, timezone
import os
import psutil
import time
import socket
import json
from confluent_kafka import Producer

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092") 
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC","metrics")
HOSTNAME = os.environ.get("NODE_NAME", "no-hostname")
collection_interval = int(os.environ.get("COLLECT_INTERVAL", "2"))



def get_system_metrics():
    # CPU usage (normalized percentage across all cores)
    per_core = psutil.cpu_percent(interval=1, percpu=True)
    avg_cpu = sum(per_core) 

    # Total CPU capacity: 100% per logical core
    num_logical_cores = psutil.cpu_count(logical=True)
    max_cpu = 100.0 * num_logical_cores

    # Memory usage
    mem = psutil.virtual_memory()
    avg_mem = mem.used / (1024 ** 2)      # in MB
    max_mem = mem.total / (1024 ** 2)     # in MB

    # Disk usage
    disk = psutil.disk_usage('/')
    avg_disk = disk.used / (1024 ** 3)    # in GB
    max_disk = disk.total / (1024 ** 3)   # in GB

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),  
        "host": HOSTNAME,
        "avg_cpu": avg_cpu,
        "avg_mem": avg_mem,
        "avg_disk": avg_disk,
        "max_cpu": max_cpu,
        "max_mem": max_mem,
        "max_disk": max_disk
    }

def delivery_report(err, msg):
    """Callback to check if message was successfully published."""
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Metrics published to {msg.topic()} [Partition {msg.partition()}]")


def send_metrics(producer, metrics):
    print(f"Sending metrics: {metrics}")
    metrics_json = json.dumps(metrics)   
    producer.produce(
        topic=KAFKA_TOPIC,
        value=metrics_json,
        callback=delivery_report
    )
    producer.flush()  

if __name__ == "__main__":
    conf = {
        "bootstrap.servers": KAFKA_BROKER,
        "client.id": socket.gethostname()
    }
    producer = Producer(conf)
    while True:
        metrics = get_system_metrics()
        send_metrics(producer,metrics)
        time.sleep(collection_interval)