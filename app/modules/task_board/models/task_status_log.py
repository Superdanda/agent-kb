import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.modules.task_board.models.task import TaskStatus


class TaskStatusLog(Base):
    __tablename__ = "task_status_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(CHAR(36), ForeignKey("tasks.id"), nullable=False, index=True)
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    
    from_status = Column(String(32), nullable=True)
    to_status = Column(String(32), nullable=False)
    change_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="status_logs")
    agent = relationship("Agent", foreign_keys=[agent_id])
