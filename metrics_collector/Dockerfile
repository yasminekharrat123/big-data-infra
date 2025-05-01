FROM python:3.9-slim
RUN pip install psutil
COPY collector.py /app/collector.py
WORKDIR /app
CMD ["python", "collector.py"]