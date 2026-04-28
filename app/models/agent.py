import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Enum, JSON, Boolean, ForeignKey, Text
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class AgentStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    agent_type = Column(String(64), nullable=True)
    device_name = Column(String(128), nullable=True)
    environment_tags = Column(JSON, nullable=True, default=list)
    capabilities = Column(Text, nullable=True)
    self_introduction = Column(Text, nullable=True)
    work_preferences = Column(JSON, nullable=True, default=dict)
    callback_url = Column(String(1024), nullable=True)
    status = Column(Enum(AgentStatus), default=AgentStatus.ACTIVE, nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    registration_request_id = Column(CHAR(36), ForeignKey("agent_registration_requests.id"), nullable=True)
    approved_by_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    credentials = relationship("AgentCredential", back_populates="agent", lazy="dynamic")
    api_nonces = relationship("ApiNonce", back_populates="agent", lazy="dynamic")
    security_events = relationship("SecurityEventLog", back_populates="agent", lazy="dynamic")
    registration_request = relationship("AgentRegistrationRequest", foreign_keys=[registration_request_id])
