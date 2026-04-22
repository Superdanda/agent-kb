from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    agent_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    device_name: Optional[str] = Field(None, max_length=128)
    environment_tags: Optional[list[str]] = None


class AgentResponse(BaseModel):
    id: str
    agent_code: str
    name: str
    device_name: Optional[str]
    environment_tags: Optional[list[str]]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CredentialCreate(BaseModel):
    agent_id: str


class CredentialResponse(BaseModel):
    id: str
    agent_id: str
    access_key: str
    status: str
    last_used_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}
