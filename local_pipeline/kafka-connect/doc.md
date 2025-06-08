# How to manage the connector in Kafka Connect?

1. Make sure the Kafka Connect container is running
2. Make sure Hadoop is running in the master container
3. To submit the `hdfs-sink` connector the Kafka Connect use:
```
 curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @./kafka-connect/hdfs-sink-connector.json
```

* To get all connectors:
    ``` curl -X GET http://localhost:8083/connectors ```

* To delete a certain connector:
    ``` curl -X DELETE http://localhost:8083/connectors/hdfs-sink ```

* To restart a connector:
    ``` curl -X POST http://localhost:8083/connectors/hdfs-sink/restart ```

* To get the status of a connector:
    ``` curl -X GET http://localhost:8083/connectors/hdfs-sink/status ```