from dataclasses import dataclass
from datetime import datetime

WAIT = 'waiting'
GO = 'go'
RUNNING = 'running'


@dataclass
class Measurement:
    id: str
    user: str
    group: str
    timestamp: datetime
    progress: float = -1
    running: bool = False
    signal: str = WAIT