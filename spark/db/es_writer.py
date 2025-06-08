from elasticsearch import Elasticsearch
from datetime import datetime
import yaml
import uuid

# === Load config ===
with open("../config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Elasticsearch config
ES_HOST = config["elasticsearch"]["host"]
ES_PORT = config["elasticsearch"]["port"]
ES_SCHEME = config["elasticsearch"].get("scheme", "http")
ES_USER = config["elasticsearch"].get("user")
ES_PASSWORD = config["elasticsearch"].get("password")
ES_ALERT_INDEX = config["elasticsearch"]["alert_index"]
ES_REPORTS_INDEX = config["elasticsearch"]["report_index"]

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

    def write_alert(self, alert):
        doc = {
            "content": alert.content,
            **alert.metadata,
        }
        print(f"Writing alert: {doc}")
        res = self.client.index(index=ES_ALERT_INDEX, id=str(uuid.uuid4()), document=doc)
        print(f"✅ Wrote alert to {ES_ALERT_INDEX}: {res['result']}")

    def write_report(self, report):
        doc = report.dict()
        doc["timestamp"] = doc["timestamp"].isoformat()  

        res = self.client.index(index=ES_REPORTS_INDEX, document=doc, id=doc["timestamp"])
        print(f"✅ Wrote report to {ES_REPORTS_INDEX} for {doc['timestamp']}: {res['result']}")
