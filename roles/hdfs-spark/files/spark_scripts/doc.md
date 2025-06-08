## How to run the spark scripts?

* Make sure Hadoop is running: you should manually execute `./start-hadoop.sh` inside the container

1. The spark_scripts volume needs to be available inside the hadoop_master container. (Through a shared volume or a copy)
2. Once inside the directory, run `zip -r app.zip` to zip the python files (PS: the `zip` utility is not available in the container)
3. Make sure that your containers (master and workers) have the needed python packages installed (pydantic pyyaml influxdb-client "elasticsearch>=8.7.0,<8.8.0")
4. Inside the directory in the master container run the command needed to submit the particular job you need:
``` 
spark-submit \
  --master yarn \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --py-files app.zip \
  --num-executors 1 \
  --conf spark.yarn.am.memory=256m\
  --conf spark.yarn.am.memoryOverhead=64m\
  metrics_streaming.py
```

```
spark-submit \
  --master yarn \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  --py-files app.zip \
  --num-executors 1 \
  --conf spark.yarn.am.memory=256m\
  --conf spark.yarn.am.memoryOverhead=64m\
  logs_streaming.py 
```

```
  spark-submit \
  --master yarn \
  --py-files app.zip \
  --num-executors 1 \
  --conf spark.yarn.am.memory=256m \
  --conf spark.yarn.am.memoryOverhead=64m\
	 batch_job.py
```


**Note**: If you are running a single hadoop worker and wish to run the jobs simultaneously you need to modify the `$HADOOP_HOME/etc/hadoop/yarn-site.xml` with the proper config. Otherwise, the scheduler will always put one of the jobs on hold. (No memory)

Here are the properties that need to be **added** to that file:
```
  <property>
      <name>yarn.scheduler.minimum-allocation-mb</name>
      <value>128</value>
  </property>

  <property>
      <name>yarn.scheduler.capacity.root.default.maximum-am-resource-percent</name>
      <value>0.5</value>
  </property>
``` 