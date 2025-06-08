from pydantic import BaseModel
from typing import Optional, Dict

class Metric(BaseModel):
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

class RawLog(BaseModel): 
    timestamp: str
    method: str
    url: str
    status: int
    contentLength: Optional[str]
    params: Optional[Dict[str, str]]
    response: Optional[Dict[str, str]]
    error: Optional[str]