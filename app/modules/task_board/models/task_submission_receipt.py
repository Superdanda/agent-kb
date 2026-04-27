import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, CHAR, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class TaskSubmissionReceipt(Base):
    __tablename__ = "task_submission_receipts"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(CHAR(36), ForeignKey("tasks.id"), nullable=False, index=True)
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False)
    result_summary = Column(Text, nullable=False)
    status = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", foreign_keys=[task_id])
    agent = relationship("Agent", foreign_keys=[agent_id])

    __table_args__ = (
        UniqueConstraint("task_id", "agent_id", "idempotency_key", name="uq_task_submission_idempotency"),
    )
