FROM python:3.9-slim
RUN pip install psutil confluent_kafka
COPY collector.py /app/collector.py
WORKDIR /app
CMD ["python", "collector.py"]