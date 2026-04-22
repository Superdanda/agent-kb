import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum, Text, CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class LearningStatus(str, PyEnum):
    NOT_LEARNED = "NOT_LEARNED"
    LEARNED = "LEARNED"
    OUTDATED = "OUTDATED"


class LearningRecord(Base):
    __tablename__ = "learning_records"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    learner_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    post_id = Column(CHAR(36), ForeignKey("posts.id"), nullable=False, index=True)
    learned_version_id = Column(CHAR(36), ForeignKey("post_versions.id"), nullable=False, index=True)
    learned_version_no = Column(Integer, nullable=False)
    status = Column(Enum(LearningStatus), default=LearningStatus.NOT_LEARNED, nullable=False)
    learn_note = Column(Text, nullable=True)
    learned_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    learner = relationship("Agent", foreign_keys=[learner_agent_id])
    post = relationship("Post", back_populates="learning_records")
    learned_version = relationship("PostVersion")
