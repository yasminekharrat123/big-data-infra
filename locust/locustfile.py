import os
import random
from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 5)

    host = os.getenv("LOCUST_HOST", "http://localhost:3000")

    @task(10)
    def greetings(self):
        self.client.get("/", name="/")

    @task(5)
    def cpu_intensive(self):
        n = random.randint(20, 45)
        self.client.get(f"/cpu?n={n}", name="/cpu")

    @task(4)
    def random_error(self):
        self.client.get("/error", name="/error")

    @task(2)
    def memory_leak(self):
        self.client.get("/memory-leak", name="/memory-leak")