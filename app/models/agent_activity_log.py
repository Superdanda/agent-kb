import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class AgentActivityLog(Base):
    __tablename__ = "agent_activity_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=True, index=True)
    action = Column(String(64), nullable=False, index=True)
    object_type = Column(String(64), nullable=False, index=True)
    object_id = Column(CHAR(36), nullable=True, index=True)
    status = Column(String(32), nullable=False)
    detail_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    agent = relationship("Agent", foreign_keys=[agent_id])
