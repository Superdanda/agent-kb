import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer, Text, CHAR, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class RatingDimension(str, PyEnum):
    QUALITY = "QUALITY"
    SPEED = "SPEED"
    COMMUNICATION = "COMMUNICATION"
    PROBLEM_SOLVING = "PROBLEM_SOLVING"
    OVERALL = "OVERALL"


class TaskRating(Base):
    __tablename__ = "task_ratings"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(CHAR(36), ForeignKey("tasks.id"), nullable=False, index=True)
    rater_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    rated_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    
    dimension = Column(String(32), nullable=False)
    score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('task_id', 'rater_agent_id', 'rated_agent_id', 'dimension', name='uq_task_rating_unique'),
    )

    task = relationship("Task", back_populates="ratings")
    rater = relationship("Agent", foreign_keys=[rater_agent_id])
    rated = relationship("Agent", foreign_keys=[rated_agent_id])
