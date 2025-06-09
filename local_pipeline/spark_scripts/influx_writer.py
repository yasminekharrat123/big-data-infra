from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

from .my_logger import get_logger
logger = get_logger(__name__)

class InfluxWriter:
    def __init__(self, url, token, org, bucket):
        try:
            self.client = InfluxDBClient(
                url=url,
                token=token,
                org=org
            )
            if not self.client.ping():
                raise ConnectionError("InfluxDB connection failed: ping was unsuccessful.")
            
            logger.info("InfluxDB client initialized and connection verified.")
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.bucket = bucket
            self.org = org
        except Exception as e:
            logger.error("Failed to initialize InfluxDB client.", exc_info=True)
            raise e

    def write_points_batch(self, points):
        if not points:
            logger.warning("Attempted to write an empty list of points to InfluxDB. No action taken.")
            return 0
        try:
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
            logger.info(f"Successfully wrote {len(points)} points to InfluxDB bucket '{self.bucket}'.")
            return len(points)
        except InfluxDBError as e:
            logger.error(f"Failed to write batch to InfluxDB bucket '{self.bucket}'.", exc_info=True)
            return 0
    
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
        self.write_points_batch(points)
        
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

        self.write_points_batch(points)