# metrics_server.py
# Listens on localhost:9999 and streams psutil metrics to any connected client (e.g. Spark).
import json
import socket
import threading
import time
from datetime import datetime
import psutil
# ─── Server Connection to Spark ────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 9999

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Waiting for Spark to connect on {HOST}:{PORT}...")
server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_sock.bind((HOST, PORT))
server_sock.listen(1)

conn, addr = server_sock.accept()
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Spark connected from {addr}")


# ─── Simulate Multiple Machines ───────────────────────────────────────────────

def simulate_machine(host):
    while True:
        # Randomized metrics for simulation
        avg_cpu = psutil.cpu_percent(interval=1)
        avg_mem = psutil.virtual_memory().percent
        avg_disk = psutil.disk_usage("/").percent
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        max_cpu = psutil.cpu_count() * 100  # Assuming max CPU usage is 100%
        max_mem = psutil.virtual_memory().total / (1024 ** 3)
        max_disk = psutil.disk_usage("/").total / (1024 ** 3)

        data = {
            "timestamp": timestamp,
            "host": host,
            "avg_cpu": avg_cpu,
            "avg_mem": avg_mem,
            "avg_disk": avg_disk,
            "max_cpu": max_cpu,
            "max_mem": max_mem,
            "max_disk": max_disk,
        }

        # Send through the connection to Spark
        try:
            conn.sendall((json.dumps(data) + "\n").encode("utf-8"))
            print(f"[{host}] Sent: {data}")
        except Exception as e:
            print(f"[{host}] Connection lost: {e}")
            break

        time.sleep(1)


# Start threads for 3 simulated machines
for i in range(1, 4):
    threading.Thread(target=simulate_machine, args=(f"machine_{i}",), daemon=True).start()

# Keep main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down server.")
finally:
    conn.close()
    server_sock.close()
