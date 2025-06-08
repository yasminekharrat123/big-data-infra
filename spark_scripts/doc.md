## How to run the spark scripts?

1. The spark_scripts volume needs to be available inside the hadoop_master container. (Through a shared volume or a copy)
2. Once inside the directory, run `zip -r app.zip` to zip the python files (PS: the `zip` utility is not available in the container)
3. Make sure that your containers (master and workers) have the needed python packages installed (pydantic pyyaml influxdb-client "elasticsearch>=8.7.0,<8.8.0")
4. Inside the directory in the master container run the command needed to submit the particular job you need:
``` spark-submit \
  --master yarn \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --py-files app.zip \
  --num-executors 1 \
  metrics_streaming.py```

  ```spark-submit \
  --master yarn \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --py-files app.zip \
  --num-executors 1 \
  logs_streaming.py```