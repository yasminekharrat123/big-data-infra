import yaml
import logging
from datetime import datetime, timezone,timedelta

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, stddev, avg, from_json, first
from pyspark.sql.types import StructType, StringType, DoubleType, IntegerType

from schema import DailyReport, Host
from es_writer import ESWriter
from initialize import initialize_sinks

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [DailyReportJob] - %(message)s')

def load_config(path="config.yaml"):
    """Loads the application configuration from a YAML file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


metrics_schema = StructType() \
    .add("timestamp", StringType()) \
    .add("host", StringType()) \
    .add("avg_cpu", DoubleType()) \
    .add("avg_mem", DoubleType()) \
    .add("avg_disk", DoubleType()) \
    .add("max_cpu", DoubleType()) \
    .add("max_mem", DoubleType()) \
    .add("max_disk", DoubleType())

log_message_schema = StructType() \
    .add("log", StringType(), True) \
    .add("node_hostname", StringType(), True) \
    .add("timestamp", StringType(), True)

log_details_schema = StructType() \
    .add("method", StringType()) \
    .add("url", StringType()) \
    .add("status", IntegerType())

def main():
    logging.info("Starting Daily Report Job.")
    config = load_config()
    es_config = config['elasticsearch']

    # 1. Initialize Sinks (Elasticsearch Index)
    report_index_name = es_config['report_index']
    report_index_mapping = {
        "properties": {
            "timestamp": {"type": "date"},
            "host_reports": {"type": "object", "enabled": False}, 
            "status_counts": {"type": "object", "enabled": False}
        }
    }
    logging.info(f"Ensuring Elasticsearch index '{report_index_name}' exists.")
    initialize_sinks(config, index_name=report_index_name, index_mapping=report_index_mapping)

    # 2. Initialize Spark Session for YARN
    spark = SparkSession.builder \
        .appName("DailyReportJob") \
        .config("spark.sql.session.timeZone", "UTC") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    logging.info("Spark Session created.")

    # 3. Define HDFS Data Paths for Today
    # The job will process data for the day it is run (in UTC).
    
    today_str = datetime.now(timezone.utc).strftime('%Y/%m/%d')
    # If you want to process data for the previous day, uncomment the next line:
    # today_str = (datetime.now(timezone.utc) - timedelta(days=1)).strftime('%Y/%m/%d')
    hdfs_base_path = config['batch']['hdfs_base_path']
    
    metrics_path = f"{hdfs_base_path}/metrics/{today_str}"
    logs_path = f"{hdfs_base_path}/logs/{today_str}"

    logging.info(f"Reading metrics from: {metrics_path}")
    logging.info(f"Reading logs from: {logs_path}")

    # 4. Process Metrics
    try:
        metrics_df = spark.read.json(metrics_path, schema=metrics_schema)
        
        metric_stats = metrics_df.groupBy("host").agg(
            avg("avg_cpu").alias("avg_cpu"),
            avg("avg_mem").alias("avg_mem"),
            avg("avg_disk").alias("avg_disk"),
            stddev("avg_cpu").alias("stddev_cpu"),
            stddev("avg_mem").alias("stddev_mem"),
            stddev("avg_disk").alias("stddev_disk"),
            first("max_cpu").alias("capacity_cpu"),
            first("max_mem").alias("capacity_mem"),
            first("max_disk").alias("capacity_disk")
        )
        
    except Exception as e:
        logging.warning(f"Could not read or process metrics from {metrics_path}. It might be empty. Error: {e}")
        metric_stats = spark.createDataFrame([], schema=StructType())


    # 5. Process Logs
    try:
        raw_logs_df = spark.read.json(logs_path)
        
        parsed_logs_df = raw_logs_df.withColumn(
            "details", from_json(col("log"), log_details_schema)
        )

        logs_df = parsed_logs_df \
            .select(
                col("node_hostname").alias("host"),
                col("details.status").alias("status")
            ) \
            .filter(col("status").isNotNull())


        categorized_logs_df = logs_df.withColumn(
            "status_category",
            when((col("status") >= 200) & (col("status") < 300), "2xx")
            .when((col("status") >= 300) & (col("status") < 400), "3xx")
            .when((col("status") >= 400) & (col("status") < 500), "4xx")
            .when((col("status") >= 500), "5xx")
            .otherwise("unknown")
        )

        status_counts_df = categorized_logs_df.groupBy("status_category").count()
    except Exception as e:
        logging.warning(f"Could not read or process logs from {logs_path}. It might be empty. Error: {e}")
        status_counts_df = spark.createDataFrame([], schema=StructType())

    # 6. Collect Results and Build the Report
    logging.info("Aggregations complete. Collecting results to driver.")
    metrics_results = metric_stats.collect()
    status_counts_results = status_counts_df.collect()

    host_reports = {}
    for row in metrics_results:
        host_reports[row["host"]] = Host(
            avg_cpu=row["avg_cpu"],
            avg_mem=row["avg_mem"],
            avg_disk=row["avg_disk"],
            stddev_cpu=row["stddev_cpu"],
            stddev_mem=row["stddev_mem"],
            stddev_disk=row["stddev_disk"],
            max_cpu=row["capacity_cpu"],
            max_mem=row["capacity_mem"],
            max_disk=row["capacity_disk"]
        )

    status_counts_dict = {row["status_category"]: row["count"] for row in status_counts_results}

    report = DailyReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        host_reports=host_reports,
        status_counts=status_counts_dict
    )

    logging.info("Successfully built the daily report object.")

    # 7. Write the Report to Elasticsearch
    try:
        es_writer = ESWriter(
            host=es_config["host"],
            port=es_config["port"],
            scheme=es_config.get("scheme", "http"),
            user=es_config.get("user"),
            password=es_config.get("password"),
            index=report_index_name,
        )
        es_writer.write_report(report)
    except Exception as e:
        logging.error(f"FATAL: Failed to write report to Elasticsearch. {e}")

    # 8. Stop Spark
    spark.stop()
    logging.info("Daily Report Job finished successfully.")


if __name__ == "__main__":
    main()