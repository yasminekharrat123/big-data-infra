from pydantic import BaseModel

class Metrics(BaseModel):
    timestamp: str
    host: str
    cpu: float
    mem: float
    disk: float
    max_cpu: float
    max_mem: float
    max_disk: float
    

class Alert(BaseModel):
    content: str
    metadata: dict