from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TaskStatusLogResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    from_status: Optional[str] = None
    to_status: str
    change_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
