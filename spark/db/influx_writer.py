from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import yaml


# === Load config ===
with open("../config.yaml", "r") as f:
    config = yaml.safe_load(f)
# InfluxDB details
INFLUX_URL = config["influx"]["url"]
INFLUX_TOKEN = config["influx"]["token"]
INFLUX_ORG = config["influx"]["org"]
INFLUX_BUCKET = config["influx"]["bucket"]

class InfluxWriter:
    def __init__(self, url= INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, bucket=INFLUX_BUCKET):
        self.client = InfluxDBClient(
            url=url,
            token=token,
            org=org
        )
        print("InfluxDB Connected:", self.client.ping())
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket
        self.org = org

    def write_metrics(self, validated_metrics):
        points = [
            Point("cpu_usage").tag("host", validated_metrics.host)
                              .field("value", validated_metrics.avg_cpu)
                              .field("allocated", validated_metrics.max_cpu)
                              .time(validated_metrics.timestamp, WritePrecision.NS),
            Point("mem_usage").tag("host", validated_metrics.host)
                              .field("value", validated_metrics.avg_mem)
                              .field("allocated", validated_metrics.max_mem)
                              .time(validated_metrics.timestamp, WritePrecision.NS),
            Point("disk_usage").tag("host", validated_metrics.host)
                               .field("value", validated_metrics.avg_disk)
                               .field("allocated", validated_metrics.max_disk)
                               .time(validated_metrics.timestamp, WritePrecision.NS),
        ]

        for point in points:
            print(f"Writing point: {point}")
        self.write_api.write(bucket=self.bucket, org=self.org, record=points)
        print(f"✅ Wrote {len(points)} points to InfluxDB")
        
        
    def write_logs(self, validated_logs):
        point = (
            Point("logs")
            .tag("status_category", validated_logs.status_category)
            .field("count", validated_logs.count)
            .time(validated_logs.timestamp, WritePrecision.NS)
        )
        print(f"Writing log point: {point}")
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
        print("✅ Wrote log point to InfluxDB")
