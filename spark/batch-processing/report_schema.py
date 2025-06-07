from pydantic import BaseModel
from typing import List, Dict
from datetime import date, datetime

class DailyReport(BaseModel):
    date: datetime
    total_requests: int
    status_distribution: dict
    avg_cpu_usage: float
    avg_memory_usage: float
    avg_disk_usage: float
    peak_cpu_time: str
    peak_memory_time: str
    peak_disk_time: str
    error_count: int
    warning_count: int
    performance_score: float
    host_metrics: dict