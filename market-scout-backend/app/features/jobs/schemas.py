from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class QueueStatus(BaseModel):
    kind: str
    queued: int
    running: int


class FailedJob(BaseModel):
    id: int
    kind: str
    ref_id: int
    attempts: int
    error: Optional[str] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class JobsStatusResponse(BaseModel):
    workers_enabled: bool
    workers_running: bool
    queues: list[QueueStatus]
    oldest_waiting_seconds: Optional[int] = None
    recent_failures: list[FailedJob]
