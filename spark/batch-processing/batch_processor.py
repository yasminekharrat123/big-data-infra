from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, stddev, avg, to_date
from report_schema import DailyReport, Host  
from db.es_writer import ESWriter
from datetime import datetime
import os

# Init Spark
spark = SparkSession.builder.appName("DailyReportJob").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

json_path = "daily_metrics.json"

df = spark.read.option("multiline", True).json(json_path)

# Add a column to distinguish between metrics and logs
df = df.withColumn("is_metric", col("avg_cpu").isNotNull())

# Separate metrics and logs
metrics_df = df.filter(col("is_metric") == True)
logs_df = df.filter(col("is_metric") == False)

# === 1. Aggregate metrics and logs ===
metric_stats = metrics_df.groupBy("host").agg(
    avg("avg_cpu").alias("avg_cpu"),
    avg("avg_mem").alias("avg_mem"),
    avg("avg_disk").alias("avg_disk"),
    stddev("avg_cpu").alias("stddev_cpu"),
    stddev("avg_mem").alias("stddev_mem"),
    stddev("avg_disk").alias("stddev_disk")
)

# === 2. Collect logs and categorize status codes ===
logs_df = logs_df.withColumn(
    "status_category",
    when((col("status") >= 200) & (col("status") < 300), "2xx")
    .when((col("status") >= 300) & (col("status") < 400), "3xx")
    .when((col("status") >= 400) & (col("status") < 500), "4xx")
    .when((col("status") >= 500), "5xx")
    .otherwise("unknown")
)

status_counts_df = logs_df.groupBy("status_category").count()

# === 3. Collect results ===
metrics = metric_stats.collect()
status_counts = status_counts_df.collect()

# === 4. Build the report ===
host_reports = {}
for row in metrics:
    host_reports[row["host"]] = Host(
        avg_cpu=row["avg_cpu"],
        avg_mem=row["avg_mem"],
        avg_disk=row["avg_disk"],
        stddev_cpu=row["stddev_cpu"],
        stddev_mem=row["stddev_mem"],
        stddev_disk=row["stddev_disk"],
    )

status_counts_dict = {row["status_category"]: row["count"] for row in status_counts}

report = DailyReport(
    timestamp=datetime.utcnow(),
    host_reports=host_reports,
    status_counts=status_counts_dict
)

# === 5. Write the report to Elasticsearch ===
es_writer = ESWriter()
es_writer.write_report(report)

# Stop Spark
spark.stop()
