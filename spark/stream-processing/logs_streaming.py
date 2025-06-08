from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, avg, last, window, current_timestamp, when
from pyspark.sql.types import StructType, StringType, IntegerType, MapType
import os
import time
import yaml
from db.es_writer import ESWriter
from db.influx_writer import InfluxWriter
from pydantic import ValidationError
from schema import Alert, Log, RawLog


log_schema = StructType() \
    .add("method", StringType()) \
    .add("url", StringType()) \
    .add("status", IntegerType()) \
    .add("contentLength", StringType()) \
    .add("params", MapType(StringType(), StringType())) \
    .add("response", MapType(StringType(), StringType())) \
    .add("error", StringType())

# Checkpoint dir
checkpoint_base = "/tmp/spark_checkpoint_logs_" + str(int(time.time()))
os.makedirs(checkpoint_base, exist_ok=True)

# === Spark session ===
spark = SparkSession.builder \
    .appName("Logs-Streaming") \
    .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/spark_checkpoint") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

stream = (
    spark.readStream
         .format("socket")
         .option("host", "127.0.0.1")
         .option("port", 9999)
         .load()
)

logs_df = stream.select(from_json(col("value"), log_schema).alias("data")).select("data.*")
logs_df = logs_df.withColumn("timestamp", current_timestamp())

logs_df = logs_df.withColumn(
    "status_category",
    when((col("status") >= 200) & (col("status") < 300), "2xx")
    .when((col("status") >= 300) & (col("status") < 400), "3xx")
    .when((col("status") >= 400) & (col("status") < 500), "4xx")
    .when((col("status") >= 500), "5xx")
    .otherwise("unknown")
)

# === Aggregated status counts ===
status_counts = logs_df.withWatermark("timestamp", "1 minute").groupBy(
    window(col("timestamp"), "1 minute"),
    col("status_category")
).count()

# === Writers ===
influx_writer = InfluxWriter()
es_writer = ESWriter()

def process_log_batch(df, batch_id):
    print(f"Processing batch {batch_id}")
    df_sorted = df.orderBy("window.start", "status_category")
    df_sorted.show(truncate=False)

    rows = df_sorted.collect()
    for row in rows:
        try:
            data = {
                "timestamp": row["window"].start.isoformat(),
                "status_category": row["status_category"],
                "count": row["count"]
            }

            validated = Log(**data)

            # ➤ Write to InfluxDB
            influx_writer.write_logs(validated)

            # ➤ Optional alert
            if validated.status_category != "2xx":
                alert = Alert(
                    content=f"{validated.count} requests with status {validated.status_category}",
                    metadata={"timestamp": validated.timestamp, "status_category": validated.status_category}
                )
                es_writer.write_alert(alert)

        except ValidationError as e:
            print(f"❌ Validation failed for row {row}: {e}")
        except Exception as e:
            print(f"❌ Failed to process row: {e}")

query_aggregated = (
    status_counts
    .writeStream
    .outputMode("update")
    .foreachBatch(process_log_batch)
    .option("checkpointLocation", checkpoint_base + "/aggregated")
    .trigger(processingTime="1 minute")
    .start()
)

# === Individual alerts for each non-2xx ===
non_2xx_logs = logs_df.filter((col("status") < 200) | (col("status") >= 300))

def process_individual_alerts(df, batch_id):
    # print(f"🔔 Processing individual alerts in batch {batch_id}")
    rows = df.collect()
    for row in rows:
        try:
            data = {
                "timestamp": row["timestamp"].isoformat(),
                "method": row["method"],
                "url": row["url"],
                "status": row["status"],
                "contentLength": row["contentLength"],
                "params": row["params"],
                "response": row["response"],
                "error": row["error"]
            }

            validated_log = RawLog(**data)

            alert = Alert(
                content=f"Non-2xx request: {validated_log.status} {validated_log.method} {validated_log.url}",
                metadata={
                    "timestamp": validated_log.timestamp,
                    "status": validated_log.status,
                    "url": validated_log.url,
                    "method": validated_log.method
                }
            )

            es_writer.write_alert(alert)

        except ValidationError as e:
            print(f"❌ Log validation failed: {e}")
        except Exception as e:
            print(f"❌ Failed to send alert: {e}")

query_individual_alerts = (
    non_2xx_logs.writeStream
    .foreachBatch(process_individual_alerts)
    .outputMode("append")
    .option("checkpointLocation", checkpoint_base + "/individual_alerts")
    .start()
)

# === Await termination ===
spark.streams.awaitAnyTermination()
