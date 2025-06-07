from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, count, avg, max as max_
from datetime import datetime
from db.es_writer import ESWriter  
from collections import defaultdict
from report_schema import DailyReport

spark = SparkSession.builder \
    .appName("DailyReportBatch") \
    .getOrCreate()

# Read data
df = spark.read.json("daily_metrics_2025-06-05.json")

# Add date column
df = df.withColumn("date", to_date(col("timestamp")))

# Collect to driver (assuming small enough to fit in memory)
data = df.collect()

# Aggregate manually in Python
records = [row.asDict() for row in data]

valid_records = [r for r in records if r["cpu"] is not None and r["memory"] is not None and r["disk"] is not None]
corrupted = [r for r in records if r not in valid_records]

if corrupted:
    print(f"⚠️ Skipped {len(corrupted)} corrupted records")

total_requests = len(valid_records)
status_dist = defaultdict(int)
host_metrics = defaultdict(lambda: {"cpu": [], "memory": [], "disk": []})

for r in valid_records:
    status_dist[r["status"]] += 1
    host_metrics[r["host"]]["cpu"].append(r["cpu"])
    host_metrics[r["host"]]["memory"].append(r["memory"])
    host_metrics[r["host"]]["disk"].append(r["disk"])

avg_cpu = sum(r["cpu"] for r in valid_records) / total_requests
avg_mem = sum(r["memory"] for r in valid_records) / total_requests
avg_disk = sum(r["disk"] for r in valid_records) / total_requests

host_avgs = {
    host: {
        "avg_cpu": sum(metrics["cpu"]) / len(metrics["cpu"]),
        "avg_memory": sum(metrics["memory"]) / len(metrics["memory"]),
        "avg_disk": sum(metrics["disk"]) / len(metrics["disk"])
    }
    for host, metrics in host_metrics.items()
}

performance_score = (100 - avg_cpu + 100 - avg_mem + 100 - avg_disk) / 3

report = DailyReport(
    date=datetime.fromisoformat(valid_records[0]["timestamp"]).date(),
    total_requests=total_requests,
    status_distribution=dict(status_dist),
    avg_cpu_usage=avg_cpu,
    avg_memory_usage=avg_mem,
    avg_disk_usage=avg_disk,
    peak_cpu_time=max(valid_records, key=lambda r: r["cpu"])["timestamp"],
    peak_memory_time=max(valid_records, key=lambda r: r["memory"])["timestamp"],
    peak_disk_time=max(valid_records, key=lambda r: r["disk"])["timestamp"],
    error_count=status_dist["error"],
    warning_count=status_dist["warning"],
    performance_score=performance_score,
    host_metrics=host_avgs
)

# Write to Elasticsearch
es_writer = ESWriter()
es_writer.write_report(report)

spark.stop()