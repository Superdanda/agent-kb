from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TaskStatusLogResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    from_status: Optional[str]
    to_status: str
    change_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
