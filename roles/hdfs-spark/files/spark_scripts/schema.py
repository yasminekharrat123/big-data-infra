import datetime
from typing import Dict, Optional
from pydantic import BaseModel

class Metrics(BaseModel):
    timestamp: str
    host: str
    avg_cpu: float
    avg_mem: float
    avg_disk: float
    max_cpu: float
    max_mem: float
    max_disk: float
    

class Alert(BaseModel):
    content: str
    metadata: dict
    
    
class Log(BaseModel):
    timestamp: str
    status_category: str
    count: int

class Host(BaseModel):
    avg_cpu: float
    avg_mem: float
    avg_disk: float
    stddev_cpu: Optional[float] = None
    stddev_mem: Optional[float] = None
    stddev_disk: Optional[float] = None
    max_cpu: float
    max_mem: float
    max_disk: float 
    
class DailyReport(BaseModel):
    timestamp: str
    host_reports: Dict[str, Host] = {}
    status_counts: Dict[str, int] 
    