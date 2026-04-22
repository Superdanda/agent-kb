import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class AgentCredential(Base):
    __tablename__ = "agent_credentials"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    access_key = Column(String(128), unique=True, nullable=False, index=True)
    secret_key_encrypted = Column(String(512), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    agent = relationship("Agent", back_populates="credentials")
