from datetime import datetime

from pydantic import BaseModel


class ApiNonceResponse(BaseModel):
    id: str
    agent_id: str
    nonce: str
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}
