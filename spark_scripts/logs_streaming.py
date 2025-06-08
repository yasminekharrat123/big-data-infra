from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, to_timestamp, when
from pyspark.sql.types import StructType, StringType, IntegerType, MapType
import yaml
from es_writer import ESWriter
from influx_writer import InfluxWriter
from schema import  Log
from initialize import initialize_sinks




# === Load config ===
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)
streaming_config = config["streaming"]
es_config = config["elasticsearch"]
influx_config = config["influx"]
kafka_config = config["kafka"]



logs_alert_mapping = {
    "properties": {
        "content": {"type": "text"},
        "timestamp": {"type": "date"},
        "status": {"type": "integer"},
        "url": {"type": "keyword"},
        "method": {"type": "keyword"},
        "host": {"type": "keyword"}
    }
}


print("--- Initializing Data Sinks for Log Stream Processor ---")
initialize_sinks(
    config=config,
    bucket_name=config["influx"]["logs_bucket"],
    index_name=config["elasticsearch"]["log_alerts_index"],
    index_mapping=logs_alert_mapping
)
print("--- Initialization Complete ---")



message_schema = StructType() \
    .add("container_name", StringType(), True) \
    .add("log", StringType(), True) \
    .add("node_hostname", StringType(), True) \
    .add("source", StringType(), True) \
    .add("container_id", StringType(), True) \
    .add("timestamp", StringType(), True)


log_schema = StructType() \
    .add("method", StringType()) \
    .add("url", StringType()) \
    .add("status", IntegerType()) \
    .add("contentLength", StringType()) \
    .add("params", MapType(StringType(), StringType())) \
    .add("response", MapType(StringType(), StringType())) \
    .add("error", StringType())

# Checkpoint dir
checkpoint_dir = streaming_config["checkpoint_dir"]

# === Spark session ===
spark = SparkSession.builder \
    .appName("Logs-Streaming") \
    .config("spark.sql.session.timeZone", "UTC") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")

stream = (
    spark.readStream
         .format("kafka")
         .option("kafka.bootstrap.servers", config["kafka"]["bootstrap_servers"])
         .option("subscribe", config["kafka"]["logs_topic"])
         .option("startingOffsets", "latest")
         .load()
)

df_raw_logs = stream.selectExpr("CAST(value AS STRING)")
df_parsed_outer = df_raw_logs.withColumn("data", from_json(col("value"), message_schema)) \
    .select("data.*") \
    .withColumn("timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss Z"))

df_with_parsed_log = df_parsed_outer.withColumn("parsed_log", from_json(col("log"), log_schema))
df_filtered = df_with_parsed_log \
    .where(col("parsed_log").isNotNull()) \
    .where(col("parsed_log.status").isNotNull())

df_final = df_filtered.select(
    "node_hostname",
    col("timestamp"), 
    "parsed_log.*"
)

df_final = df_final.withColumn(
    "status_category",
    when((col("status") >= 200) & (col("status") < 300), "2xx")
    .when((col("status") >= 300) & (col("status") < 400), "3xx")
    .when((col("status") >= 400) & (col("status") < 500), "4xx")
    .when((col("status") >= 500), "5xx")
    .otherwise("unknown")
)

# === Aggregated status counts ===
status_counts = df_final.withWatermark("timestamp", "10 seconds").groupBy(
    window(col("timestamp"), "15 seconds"),
    col("status_category")
).count()

def process_aggregated_logs_batch(df, batch_id):
    if df.rdd.isEmpty():
        return

    def write_partition(partition_of_rows):
        influx_writer = InfluxWriter(
            url=influx_config["url"], token=influx_config["token"],
            org=influx_config["org"], bucket=influx_config["logs_bucket"]
        )

        logs_to_write = []

        for row in partition_of_rows:
            # Prepare data for InfluxDB
            validated_log = Log(
                timestamp=row["window"].start.isoformat(),
                status_category=row["status_category"],
                count=row["count"]
            )
            logs_to_write.append(validated_log)
        
        # Perform bulk writes
        try:
            if logs_to_write:
                influx_writer.write_logs(logs_to_write)
            print(f"✅ Processed aggregated batch: {len(logs_to_write)} log counts")
        except Exception as e:
            print(f"❌ Failed to write aggregated batch data: {e}")

    df.foreachPartition(write_partition)

query_aggregated = (
    status_counts
    .writeStream
    .outputMode("update")
    .foreachBatch(process_aggregated_logs_batch)
    .option("checkpointLocation", f"{checkpoint_dir}/aggregated_logs")
    .trigger(processingTime=f"{streaming_config['minibatch_interval']} seconds")
    .start()
)

# === Individual alerts for each non-2xx ===
non_2xx_logs_df = df_final.filter((col("status") < 200) | (col("status") >= 300))

def process_individual_alerts_batch(df, batch_id):
    if df.rdd.isEmpty():
        return

    def write_partition(partition_of_rows):
        es_writer = ESWriter(
            host=es_config["host"], port=es_config["port"], scheme=es_config.get("scheme", "http"),
            user=es_config.get("user"), password=es_config.get("password"),
            index=es_config["log_alerts_index"]
        )

        alerts_to_write = []

        for row in partition_of_rows:
            alert = {
                "content": f"Alert: {row['status']} {row['method']} {row['url']}",
                "metadata": {
                    "timestamp": row["timestamp"].isoformat(),
                    "status": row["status"],
                    "url": row["url"],
                    "method": row["method"],
                    "host": row["node_hostname"],
                }
            }
            alerts_to_write.append(alert)
        
        try:
            if alerts_to_write:
                es_writer.write_alerts_batch(alerts_to_write)
            print(f"✅ Processed individual alert batch with {len(alerts_to_write)} alerts.")
        except Exception as e:
            print(f"❌ Failed to write individual alert batch data: {e}")
    
    df.foreachPartition(write_partition)

query_individual_alerts = (
    non_2xx_logs_df.writeStream
    .foreachBatch(process_individual_alerts_batch)
    .outputMode("append")
    .option("checkpointLocation", checkpoint_dir + "/individual_alerts")
    .trigger(processingTime=f"{streaming_config['minibatch_interval']} seconds")
    .start()
)



# === Await termination ===
spark.streams.awaitAnyTermination()