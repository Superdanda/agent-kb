from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentRegistrationCreate(BaseModel):
    agent_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    device_name: Optional[str] = Field(None, max_length=128)
    environment_tags: Optional[list[str]] = None
    capabilities: Optional[str] = None
    self_introduction: Optional[str] = None


class AgentRegistrationRequestSchema(BaseModel):
    id: str
    registration_code: str
    agent_code: str
    name: str
    device_name: Optional[str]
    environment_tags: Optional[list[str]]
    capabilities: Optional[str]
    self_introduction: Optional[str]
    status: str
    rejection_reason: Optional[str]
    admin_notes: Optional[str]
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRegistrationResponse(BaseModel):
    id: str
    registration_code: str
    agent_code: str
    name: str
    device_name: Optional[str]
    environment_tags: Optional[list[str]]
    capabilities: Optional[str]
    self_introduction: Optional[str]
    status: str
    status_text: str
    rejection_reason: Optional[str]
    admin_notes: Optional[str]
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_request(cls, req) -> "AgentRegistrationResponse":
        status_text_map = {
            "PENDING": "Pending Approval",
            "APPROVED": "Approved",
            "REJECTED": "Rejected",
        }
        return cls(
            id=req.id,
            registration_code=req.registration_code,
            agent_code=req.agent_code,
            name=req.name,
            device_name=req.device_name,
            environment_tags=req.environment_tags,
            capabilities=req.capabilities,
            self_introduction=req.self_introduction,
            status=req.status.value if hasattr(req.status, 'value') else req.status,
            status_text=status_text_map.get(req.status.value if hasattr(req.status, 'value') else req.status, "Unknown"),
            rejection_reason=req.rejection_reason,
            admin_notes=req.admin_notes,
            approved_at=req.approved_at,
            approved_by=req.approved_by,
            created_at=req.created_at,
        )


class AgentCredentialsResponse(BaseModel):
    registration_code: str
    agent_id: str
    agent_code: str
    name: str
    access_key: str
    secret_key: str

    model_config = {"from_attributes": True}
