import os
import psutil
import time
import socket
import json
from confluent_kafka import Producer

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092") 
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC","metrics")




def get_system_metrics():
    # CPU usage
    cpu_usage = psutil.cpu_percent(interval=1)
    
    # Memory usage
    memory = psutil.virtual_memory()
    memory_usage = {
        "total": memory.total,
        "used": memory.used,
        "percent": memory.percent
    }
    
    # Disk usage
    disk = psutil.disk_usage('/')
    disk_usage = {
        "total": disk.total,
        "used": disk.used,
        "percent": disk.percent
    }
    
    return {
        "hostname": socket.gethostname(),
        "cpu_percent": cpu_usage,
        "memory": memory_usage,
        "disk": disk_usage,
        "timestamp": time.time()
    }

def delivery_report(err, msg):
    """Callback to check if message was successfully published."""
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Metrics published to {msg.topic()} [Partition {msg.partition()}]")


def send_metrics(producer, metrics):
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
        time.sleep(2)  # Collect and send every 2 seconds