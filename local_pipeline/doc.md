## How to run the pipeline?

1. Head over to the docker compose file, pick the containers needed for what you are about to test.
2. Run `docker compose up`
3. Docker exec into the Hadoop master container and run `./start-hadoop.sh`
4. If you're using kafka connect, head over to `kafka-connect/doc.md` for more information on how to submit the HDFS connector
5. If you want to run a spark app (one of the streaming apps or the batch app), head over to `spark-scripts/doc.md` for more information.
6. If you want to simulate a load on the app (during logs streaming): run the locust script found at the folder at the root of the project


* You can vizualize the alerts/report on Kibana. 
* You can vizualize the hardware-metrics/logs-metrics on InfluxDB UI.