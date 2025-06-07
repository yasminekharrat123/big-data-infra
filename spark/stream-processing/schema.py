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
    
    
class Logs(BaseModel):
    timestamp: str
    status_category: str
    count: int
    