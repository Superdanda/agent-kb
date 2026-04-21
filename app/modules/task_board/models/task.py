import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum, JSON, Text, CHAR, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class TaskPriority(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskDifficulty(str, PyEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"


class TaskStatus(str, PyEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    created_by_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    assigned_to_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=True, index=True)
    domain_id = Column(CHAR(36), ForeignKey("knowledge_domains.id"), nullable=True, index=True)
    
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    difficulty = Column(Enum(TaskDifficulty), nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    
    points = Column(Integer, default=0, nullable=False)
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)
    
    tags_json = Column(JSON, nullable=True, default=list)
    metadata_json = Column(JSON, nullable=True, default=dict)
    
    due_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    created_by = relationship("Agent", foreign_keys=[created_by_agent_id])
    assigned_to = relationship("Agent", foreign_keys=[assigned_to_agent_id])
    domain = relationship("KnowledgeDomain")
    
    materials = relationship("TaskMaterial", back_populates="task", lazy="dynamic")
    status_logs = relationship("TaskStatusLog", back_populates="task", lazy="dynamic", order_by="TaskStatusLog.created_at")
    ratings = relationship("TaskRating", back_populates="task", lazy="dynamic")
