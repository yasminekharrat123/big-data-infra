from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.functions import (
    regexp_extract, to_timestamp, window, avg, last, unix_timestamp, current_timestamp, expr
)
import yaml
from pyspark.sql.types import StructType, StringType, DoubleType, IntegerType, TimestampType
import os
import time
from pydantic import ValidationError
from schema import Metrics, Alert


# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Extract thresholds
CPU_THRESHOLD = config["thresholds"]["cpu"]
MEM_THRESHOLD = config["thresholds"]["mem"]
DISK_THRESHOLD = config["thresholds"]["disk"]

 # Extract InfluxDB connection details
INFLUX_URL    = config["influx"]["url"]
INFLUX_TOKEN  = config["influx"]["token"]
INFLUX_ORG    = config["influx"]["org"]
INFLUX_BUCKET = config["influx"]["bucket"]

print(f"InfluxDB Token: {INFLUX_TOKEN}")

 # Initialize InfluxDB client
influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
print(influx_client.ping())
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

schema = StructType() \
    .add("timestamp", TimestampType()) \
    .add("host", StringType()) \
    .add("avg_cpu", DoubleType()) \
    .add("avg_mem", DoubleType()) \
    .add("avg_disk", DoubleType())\
    .add("max_cpu", DoubleType()) \
    .add("max_mem", DoubleType()) \
    .add("max_disk", DoubleType())

# Create a directory for checkpointing
checkpoint_dir = "/tmp/spark_checkpoint_" + str(int(time.time()))
os.makedirs(checkpoint_dir, exist_ok=True)

# Initialize Spark session
spark = SparkSession.builder \
    .appName("HW-Metrics-Streaming") \
    .config("spark.hadoop.fs.file.impl", "org.apache.hadoop.fs.LocalFileSystem") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/spark_checkpoint") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

# Create a socket stream
stream = (
    spark.readStream
         .format("socket")
         .option("host", "127.0.0.1")
         .option("port", 9999)
         .load()
)

# Parse the stream as JSON
parsed = (
    stream
    .select(from_json(col("value"), schema).alias("data"))
    .select("data.*")
    .withColumn("timestamp", col("timestamp").cast("timestamp"))
)

# Tumbling window to calculate moving averages
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


def log_batch(df, batch_id):
    print(f"Logging data for batch {batch_id}")
    df_sorted = df.orderBy("window.start", "host")
    df_sorted.show(truncate=False)

    rows = df_sorted.collect()
    for row in rows:
        try:
            points=[]
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
            
            points.extend([
                Point("cpu_usage").tag("host", validated.host)
                                .field("value", validated.avg_cpu)
                                .field("allocated", validated.max_cpu)
                                .time(validated.timestamp, WritePrecision.NS),
                Point("mem_usage").tag("host", validated.host)
                                .field("value", validated.avg_mem)
                                .field("allocated", validated.max_mem)
                                .time(validated.timestamp, WritePrecision.NS),
                Point("disk_usage").tag("host", validated.host)
                                .field("value", validated.avg_disk)
                                .field("allocated", validated.max_disk)
                                .time(validated.timestamp, WritePrecision.NS),
            ])
            # Write to InfluxDB
            if points:
                for point in points:
                    print(f"Writing point: {point}")
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
                print(f"✅ Wrote {len(points)} points to InfluxDB for batch {batch_id}")
        
            alerts = []
            if validated.avg_cpu > CPU_THRESHOLD:
                alerts.append(Alert(
                    content=f"⚠️ High CPU usage on {validated.host}: {validated.avg_cpu:.2f}%",
                    metadata={"host": validated.host, "metric": "cpu", "value": validated.avg_cpu, "threshold": CPU_THRESHOLD}
                ))
            if validated.avg_mem > MEM_THRESHOLD:
                alerts.append(Alert(
                    content=f"⚠️ High Memory usage on {validated.host}: {validated.avg_mem:.2f}%",
                    metadata={"host": validated.host, "metric": "mem", "value": validated.avg_mem, "threshold": MEM_THRESHOLD}
                ))
            if validated.avg_disk > DISK_THRESHOLD:
                alerts.append(Alert(
                    content=f"⚠️ High Disk usage on {validated.host}: {validated.avg_disk:.2f}%",
                    metadata={"host": validated.host, "metric": "disk", "value": validated.avg_disk, "threshold": DISK_THRESHOLD}
                ))

            if alerts:
                print(f"🚨 ALERTS for {validated.host} 🚨")
                for alert in alerts:
                    print(alert.model_dump_json(indent=2))  
                    
        except ValidationError as e:
            print(f"❌ Validation failed for row {row}: {e}")
            
        except Exception as e:
            print(f"❌ Failed to write point: {e}")



#Write the data to the console and log each batch
query = (
    tumbling
      .writeStream
      .outputMode("complete")
      .foreachBatch(log_batch)  # Log each batch of data
      .option("checkpointLocation", checkpoint_dir)
      .trigger(processingTime='10 seconds')
      .start()
)

# Wait for the termination of the stream
spark.streams.awaitAnyTermination()
