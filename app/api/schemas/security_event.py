from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SecurityEventLogResponse(BaseModel):
    id: str
    event_type: str
    agent_id: Optional[str]
    detail: Optional[str]
    source_ip: Optional[str]
    created_at: datetime
    agent_name: Optional[str] = None

    model_config = {"from_attributes": True}
