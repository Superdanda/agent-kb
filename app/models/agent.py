import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Enum, JSON
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class AgentStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    device_name = Column(String(128), nullable=True)
    environment_tags = Column(JSON, nullable=True, default=list)
    status = Column(Enum(AgentStatus), default=AgentStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    credentials = relationship("AgentCredential", back_populates="agent", lazy="dynamic")
    api_nonces = relationship("ApiNonce", back_populates="agent", lazy="dynamic")
    security_events = relationship("SecurityEventLog", back_populates="agent", lazy="dynamic")
