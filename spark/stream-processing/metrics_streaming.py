from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, avg, last, window
from pyspark.sql.types import StructType, StringType, DoubleType, TimestampType
from db.influx_writer import InfluxWriter
from pydantic import ValidationError
from schema import Metrics, Alert
from db.es_writer import ESWriter
import yaml
import os
import time

# === Load config ===
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Thresholds
CPU_THRESHOLD = config["thresholds"]["cpu"]
MEM_THRESHOLD = config["thresholds"]["mem"]
DISK_THRESHOLD = config["thresholds"]["disk"]

# === Initialize InfluxDB Writer ===
influx_writer = InfluxWriter()

# === Initialize Elasticsearch Writer ===
es_writer = ESWriter()

# === Define Spark schema ===
schema = StructType() \
    .add("timestamp", TimestampType()) \
    .add("host", StringType()) \
    .add("avg_cpu", DoubleType()) \
    .add("avg_mem", DoubleType()) \
    .add("avg_disk", DoubleType()) \
    .add("max_cpu", DoubleType()) \
    .add("max_mem", DoubleType()) \
    .add("max_disk", DoubleType())

# Checkpoint dir
checkpoint_dir = "/tmp/spark_checkpoint_" + str(int(time.time()))
os.makedirs(checkpoint_dir, exist_ok=True)

# === Spark session ===
spark = SparkSession.builder \
    .appName("HW-Metrics-Streaming") \
    .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/spark_checkpoint") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# === Read from socket ===
stream = (
    spark.readStream
         .format("socket")
         .option("host", "127.0.0.1")
         .option("port", 9999)
         .load()
)

# === Parse JSON ===
parsed = (
    stream
    .select(from_json(col("value"), schema).alias("data"))
    .select("data.*")
    .withColumn("timestamp", col("timestamp").cast("timestamp"))
)

# === Tumbling window aggregation ===
tumbling = (
    parsed
    .withWatermark("timestamp", "10 seconds")
    .groupBy(
        window(col("timestamp"), "30 seconds"),
        col("host")
    )
    .agg(
        avg("avg_cpu").alias("avg_cpu"),
        avg("avg_mem").alias("avg_mem"),
        avg("avg_disk").alias("avg_disk"),
        last("max_cpu").alias("max_cpu"),
        last("max_mem").alias("max_mem"),
        last("max_disk").alias("max_disk")
    )
)

# === Batch processing function ===
def log_batch(df, batch_id):
    print(f"Logging data for batch {batch_id}")
    df_sorted = df.orderBy("window.start", "host")
    df_sorted.show(truncate=False)

    rows = df_sorted.collect()
    for row in rows:
        try:
            data = {
                "timestamp": row["window"].start.isoformat(),
                "host": row["host"],
                "avg_cpu": row["avg_cpu"],
                "avg_mem": row["avg_mem"],
                "avg_disk": row["avg_disk"],
                "max_cpu": row["max_cpu"],
                "max_mem": row["max_mem"],
                "max_disk": row["max_disk"]
            }

            validated = Metrics(**data)

            # ➤ Write to InfluxDB
            influx_writer.write_metrics(validated)

            # ➤ Alert checks (unchanged)
            alerts = []
            if validated.avg_cpu > CPU_THRESHOLD:
                alerts.append(Alert(
                    content=f"⚠️ High CPU usage on {validated.host}: {validated.avg_cpu:.2f}%",
                    metadata={"timestamp":validated.timestamp, "host": validated.host, "metric": "cpu", "value": validated.avg_cpu, "threshold": CPU_THRESHOLD}
                ))
            if validated.avg_mem > MEM_THRESHOLD:
                alerts.append(Alert(
                    content=f"⚠️ High Memory usage on {validated.host}: {validated.avg_mem:.2f}%",
                    metadata={"timestamp":validated.timestamp, "host": validated.host, "metric": "mem", "value": validated.avg_mem, "threshold": MEM_THRESHOLD}
                ))
            if validated.avg_disk > DISK_THRESHOLD:
                alerts.append(Alert(
                    content=f"⚠️ High Disk usage on {validated.host}: {validated.avg_disk:.2f}%",
                    metadata={"timestamp":validated.timestamp, "host": validated.host, "metric": "disk", "value": validated.avg_disk, "threshold": DISK_THRESHOLD}
                ))

            if alerts:
                print(f"🚨 ALERTS for {validated.host} 🚨")
                for alert in alerts:
                    print(alert.model_dump_json(indent=2))
                    try:
                        es_writer.write_alert(alert)
                    except Exception as e:
                        print(f"❌ Failed to write alert to Elasticsearch: {e}")

        except ValidationError as e:
            print(f"❌ Validation failed for row {row}: {e}")
        except Exception as e:
            print(f"❌ Failed to process row: {e}")

# === Start streaming query ===
query = (
    tumbling
    .writeStream
    .outputMode("complete")
    .foreachBatch(log_batch)
    .option("checkpointLocation", checkpoint_dir)
    .trigger(processingTime='10 seconds')
    .start()
)

# === Await termination ===
spark.streams.awaitAnyTermination()
