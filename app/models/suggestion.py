import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class SuggestionCategory(str, PyEnum):
    PLATFORM_FEEDBACK = "platform_feedback"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    OTHER = "other"


class SuggestionStatus(str, PyEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class SuggestionPriority(str, PyEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default=SuggestionStatus.PENDING.value)
    priority = Column(String(16), default=SuggestionPriority.NORMAL.value)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    agent = relationship("Agent", foreign_keys=[agent_id])
    replies = relationship("SuggestionReply", back_populates="suggestion", lazy="dynamic")


class SuggestionReply(Base):
    __tablename__ = "suggestion_replies"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    suggestion_id = Column(CHAR(36), ForeignKey("suggestions.id"), nullable=False, index=True)
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    suggestion = relationship("Suggestion", back_populates="replies")
    agent = relationship("Agent", foreign_keys=[agent_id])
