from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CredentialResponse(BaseModel):
    id: str
    agent_id: str
    access_key: str
    status: str
    last_used_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
