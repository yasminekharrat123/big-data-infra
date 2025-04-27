import psutil
import time
import socket
import json

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

def send_metrics(metrics):
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    while True:
        metrics = get_system_metrics()
        send_metrics(metrics)
        time.sleep(2)  # Collect and send every 2 seconds