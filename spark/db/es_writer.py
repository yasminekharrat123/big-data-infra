from elasticsearch import Elasticsearch
from datetime import datetime
import yaml
import uuid

# === Load config ===
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Elasticsearch config
ES_HOST = config["elasticsearch"]["host"]
ES_PORT = config["elasticsearch"]["port"]
ES_SCHEME = config["elasticsearch"].get("scheme", "http")
ES_USER = config["elasticsearch"].get("user")
ES_PASSWORD = config["elasticsearch"].get("password")
ES_ALERT_INDEX = config["elasticsearch"]["alert_index"]
ES_REPORTS_INDEX = config["elasticsearch"].get["report_index"]

class ESWriter:
    def __init__(self):
        self.client = Elasticsearch(
            f"{ES_SCHEME}://{ES_HOST}:{ES_PORT}",
            basic_auth=(ES_USER, ES_PASSWORD),
            headers={
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            },
            verify_certs=False
        )

        if not self.client.ping():
            print(self.client.info())
            raise ConnectionError("Cannot connect to Elasticsearch")
        print("✅ Connected to Elasticsearch")

        self._ensure_report_index_exists()

    def _ensure_report_index_exists(self):
        if not self.client.indices.exists(index=ES_REPORTS_INDEX):
            self.client.indices.create(
                index=ES_REPORTS_INDEX,
                mappings={
                    "properties": {
                        "date": {"type": "date"},
                        "total_requests": {"type": "integer"},
                        "status_distribution": {"type": "object"},
                        "avg_cpu_usage": {"type": "float"},
                        "avg_memory_usage": {"type": "float"},
                        "avg_disk_usage": {"type": "float"},
                        "peak_cpu_time": {"type": "text"},
                        "peak_memory_time": {"type": "text"},
                        "peak_disk_time": {"type": "text"},
                        "error_count": {"type": "integer"},
                        "warning_count": {"type": "integer"},
                        "performance_score": {"type": "float"},
                        "host_metrics": {"type": "object"}
                    }
                }
            )
            print(f"🆕 Created report index: {ES_REPORTS_INDEX}")

    def write_alert(self, alert):
        doc = {
            "content": alert.content,
            **alert.metadata,
        }
        res = self.client.index(index=ES_ALERT_INDEX, id=str(uuid.uuid4()), document=doc)
        print(f"✅ Wrote alert to {ES_ALERT_INDEX}: {res['result']}")

    def write_report(self, report):
        doc = report.dict()
        doc["date"] = doc["date"].isoformat()  

        res = self.client.index(index=ES_REPORTS_INDEX, document=doc, id=doc["date"])
        print(f"✅ Wrote report to {ES_REPORTS_INDEX} for {doc['date']}: {res['result']}")
