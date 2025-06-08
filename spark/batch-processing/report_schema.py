from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import date, datetime

class Host(BaseModel):
    avg_cpu: float
    avg_mem: float
    avg_disk: float
    stddev_cpu: Optional[float] = None
    stddev_mem: Optional[float] = None
    stddev_disk: Optional[float] = None
    
class DailyReport(BaseModel):
    timestamp: datetime
    host_reports: Dict[str, Host] = {}
    status_counts: Dict[str, int] 
    