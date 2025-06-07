# logs_server.py
import json
import socket
import threading
import time
import random
from datetime import datetime

# ─── Server Setup ──────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 9999

print(f"[{datetime.now()}] Waiting for Spark to connect on {HOST}:{PORT}...")
server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_sock.bind((HOST, PORT))
server_sock.listen(1)

conn, addr = server_sock.accept()
print(f"[{datetime.now()}] Spark connected from {addr}")

# ─── Sample Data ───────────────────────────────────────────────────────────────
methods = ["GET", "POST", "PUT", "DELETE"]
urls = ["/api/data", "/api/user", "/api/update", "/login", "/register"]
status_codes = [200, 201, 204, 400, 401, 403, 404, 500, 502, 503]
errors = ["", "TimeoutError", "ConnectionRefusedError", "InternalServerError"]

# ─── Simulate Log Entry Generation ─────────────────────────────────────────────

def simulate_logs():
    while True:
        log_entry = {
            "method": random.choice(methods),
            "url": random.choice(urls),
            "status": random.choice(status_codes),
            "contentLength": str(random.randint(100, 5000)),
            "params": {"q": "test", "id": str(random.randint(1, 100))},
            "response": {"msg": "OK" if random.random() > 0.2 else "Error"},
            "error": random.choices(errors, weights=[0.8, 0.05, 0.1, 0.05])[0]
        }

        try:
            conn.sendall((json.dumps(log_entry) + "\n").encode("utf-8"))
            print(f"[{datetime.now()}] Sent: {log_entry}")
        except Exception as e:
            print(f"Connection lost: {e}")
            break

        time.sleep(random.uniform(0.5, 2))  # Irregular intervals

# ─── Start Simulation ──────────────────────────────────────────────────────────
try:
    simulate_logs()
except KeyboardInterrupt:
    print("Shutting down log server.")
finally:
    conn.close()
    server_sock.close()
