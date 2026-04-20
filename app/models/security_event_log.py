import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class SecurityEventLog(Base):
    __tablename__ = "security_event_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(64), nullable=False, index=True)
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=True, index=True)
    detail = Column(Text, nullable=True)
    source_ip = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    agent = relationship("Agent", back_populates="security_events")
