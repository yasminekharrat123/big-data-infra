from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

class InfluxWriter:
    def __init__(self, url, token, org, bucket):
        self.client = InfluxDBClient(
            url=url,
            token=token,
            org=org
        )
        print("InfluxDB Connected:", self.client.ping())
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket
        self.org = org

    def write_points_batch(self, points):
        if not points:
            return 0
        self.write_api.write(bucket=self.bucket, org=self.org, record=points)
        return len(points)
    
    def write_metrics(self, validated_metrics):
        points = []
        for metrics in validated_metrics:
            points.extend([
                Point("cpu_usage").tag("host", metrics.host)
                                .field("value", metrics.avg_cpu)
                                .field("allocated", metrics.max_cpu)
                                .time(metrics.timestamp, WritePrecision.NS),
                Point("mem_usage").tag("host", metrics.host)
                                .field("value", metrics.avg_mem)
                                .field("allocated", metrics.max_mem)
                                .time(metrics.timestamp, WritePrecision.NS),
                Point("disk_usage").tag("host", metrics.host)
                                .field("value", metrics.avg_disk)
                                .field("allocated", metrics.max_disk)
                                .time(metrics.timestamp, WritePrecision.NS),
            ])
        num_written = self.write_points_batch(points)
        if num_written == 0:
            print("⚠️ No points written to InfluxDB.")
        else:
            print(f"✅ Successfully wrote {num_written} points to InfluxDB.")
        
    def write_logs(self, validated_logs):
        points = []
        for log_agg in validated_logs:
            point = (
                Point("log_status_counts")
                .tag("status_category", log_agg.status_category)
                .field("count", log_agg.count)
                .time(log_agg.timestamp, WritePrecision.NS)
            )
            points.append(point)

        num_written = self.write_points_batch(points)
        print(f"✅ Successfully wrote {num_written} log points to InfluxDB.")