from es_writer import ESWriter
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, avg, last, window, to_timestamp
from pyspark.sql.types import StructType, StringType, DoubleType
from influx_writer import InfluxWriter

from schema import Metrics
import yaml

from initialize import initialize_sinks

from logger import get_logger
logger = get_logger(__name__)

# === Load config ===
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Thresholds
CPU_THRESHOLD = config["thresholds"]["cpu"]
MEM_THRESHOLD = config["thresholds"]["mem"]
DISK_THRESHOLD = config["thresholds"]["disk"]
es_config = config["elasticsearch"]
streaming_config = config["streaming"]
# Checkpoint dir
checkpoint_dir = streaming_config["checkpoint_dir"]

logger.info("Loaded configuration successfully.")


metrics_alert_mapping = {
    "properties": {
        "content": {"type": "text"},
        "timestamp": {"type": "date"},
        "host": {"type": "keyword"},
        "metric": {"type": "keyword"},
        "value": {"type": "float"},
        "threshold": {"type": "float"}
    }
}

logger.info("Initializing Data Sinks for Metrics Processor")
initialize_sinks(
    config=config,
    bucket_name=config["influx"]["metrics_bucket"],
    index_name=config["elasticsearch"]["metrics_alert_index"],
    index_mapping=metrics_alert_mapping
)
logger.info("Initialization Complete")


# === Define Spark schema ===
schema = StructType() \
    .add("timestamp", StringType()) \
    .add("host", StringType()) \
    .add("avg_cpu", DoubleType()) \
    .add("avg_mem", DoubleType()) \
    .add("avg_disk", DoubleType()) \
    .add("max_cpu", DoubleType()) \
    .add("max_mem", DoubleType()) \
    .add("max_disk", DoubleType())


# === Spark session ===
spark = SparkSession.builder \
    .appName("HW-Metrics-Streaming") \
    .config("spark.sql.session.timeZone", "UTC") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# === Read from Kafka ===
stream = (
    spark.readStream
         .format("kafka")
         .option("kafka.bootstrap.servers", config["kafka"]["bootstrap_servers"])
         .option("subscribe", config["kafka"]["metrics_topic"])
         .option("startingOffsets", "latest")
         .load()
)

# === Parse JSON ===
parsed = (
    stream
    .select(from_json(col("value").cast("string"), schema).alias("data"))
    .select("data.*")
    .withColumn("timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXX"))
)

# === Tumbling window aggregation ===
tumbling = (
    parsed
    .withWatermark("timestamp", f"{streaming_config['metrics_watermark_interval']} seconds")
    .groupBy(
        window(col("timestamp"), f"{streaming_config['metrics_tumble_interval']} seconds"),
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


def build_alerts(validated):
    alerts = []
    if validated.avg_cpu > CPU_THRESHOLD:
        alerts.append({
            "content": f"⚠️ High CPU usage on {validated.host}: {validated.avg_cpu:.2f}%",
            "metadata": {
                "timestamp": validated.timestamp,
                "host": validated.host,
                "metric": "cpu",
                "value": validated.avg_cpu,
                "threshold": CPU_THRESHOLD
            }
        })
    if validated.avg_mem > MEM_THRESHOLD:
        alerts.append({
            "content": f"⚠️ High Memory usage on {validated.host}: {validated.avg_mem:.2f}",
            "metadata": {
                "timestamp": validated.timestamp,
                "host": validated.host,
                "metric": "mem",
                "value": validated.avg_mem,
                "threshold": MEM_THRESHOLD
            }
        })
    if validated.avg_disk > DISK_THRESHOLD:
        alerts.append({
            "content": f"⚠️ High Disk usage on {validated.host}: {validated.avg_disk:.2f}",
            "metadata": {
                "timestamp": validated.timestamp,
                "host": validated.host,
                "metric": "disk",
                "value": validated.avg_disk,
                "threshold": DISK_THRESHOLD
            }
        })
    return alerts


def process_and_write_batch(df, batch_id):
    logger.info(f"--- Processing Batch ID: {batch_id} ---")
    if df.rdd.isEmpty():
        logger.info(f"Batch ID: {batch_id} is empty. Skipping.")
        return

    # This function will run on each executor for its partition of data
    def write_partition(partition_of_rows):
        partition_logger = get_logger(__name__)

        try:
            influx_writer = InfluxWriter(
                url=config["influx"]["url"],
                token=config["influx"]["token"],
                org=config["influx"]["org"],
                bucket=config["influx"]["metrics_bucket"]
            )

            es_writer = ESWriter(
                host=es_config["host"],
                port=es_config["port"],
                scheme=es_config.get("scheme", "http"),
                user=es_config.get("user"),
                password=es_config.get("password"),
                index=es_config["metrics_alert_index"],
            )
        except Exception as e:
            partition_logger.error("Failed to initialize data writers on executor.", exc_info=True)
            return

        alerts = []
        validated_data = []

        for row in partition_of_rows:
            try:
                # Convert row to Pydantic model for validation
                data = {
                    "timestamp": row["window"].start.isoformat(),
                    "host": row["host"],
                    "avg_cpu": row["avg_cpu"], "avg_mem": row["avg_mem"], "avg_disk": row["avg_disk"],
                    "max_cpu": row["max_cpu"], "max_mem": row["max_mem"], "max_disk": row["max_disk"]
                }
                validated = Metrics(**data)
                validated_data.append(validated)
                alerts.extend(build_alerts(validated))
            except Exception as e:
                partition_logger.error(f"Failed to validate or process row: {row}", exc_info=True)

        # Write the entire list of points for this partition in one network call
        try:
            if validated_data:
                influx_writer.write_metrics(validated_data)
            if alerts:
                es_writer.write_alerts_batch(alerts)
            
            if validated_data or alerts:
                partition_logger.info(f"Successfully wrote {len(validated_data)} metrics and {len(alerts)} alerts for this partition.")
            
        except Exception as e:
            partition_logger.error("Failed to write data partition to sinks.", exc_info=True)

    # Apply the write function to each partition in parallel
    df.foreachPartition(write_partition)
    logger.info(f"--- Finished Processing Batch ID: {batch_id} ---")



# === Start streaming query ===
query = (
    tumbling
    .writeStream
    .outputMode("update")
    .foreachBatch(process_and_write_batch)
    .option("checkpointLocation", checkpoint_dir + "/metrics_streaming")
    .trigger(processingTime=f"{streaming_config['metrics_minibatch_interval']} seconds")
    .start()
)

logger.info("Streaming query started. Waiting for data from Kafka...")



# === Await termination ===
spark.streams.awaitAnyTermination()


