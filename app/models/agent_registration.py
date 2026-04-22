import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Text, JSON, Enum

from app.core.database import Base


class RegistrationStatus(str, PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AgentRegistrationRequest(Base):
    __tablename__ = "agent_registration_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    registration_code = Column(String(16), unique=True, nullable=False, index=True)
    agent_code = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    device_name = Column(String(128), nullable=True)
    environment_tags = Column(JSON, nullable=True, default=list)
    capabilities = Column(Text, nullable=True)
    self_introduction = Column(Text, nullable=True)
    status = Column(Enum(RegistrationStatus), default=RegistrationStatus.PENDING, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
