import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum, Text, CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChangeType(str, PyEnum):
    MINOR = "MINOR"
    MAJOR = "MAJOR"


class PostVersion(Base):
    __tablename__ = "post_versions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(CHAR(36), ForeignKey("posts.id"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    title_snapshot = Column(String(512), nullable=False)
    summary_snapshot = Column(Text, nullable=True)
    content_md = Column(Text, nullable=True)
    change_type = Column(Enum(ChangeType), nullable=False)
    change_note = Column(Text, nullable=True)
    created_by_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    post = relationship("Post", back_populates="versions", foreign_keys=[post_id])
    created_by_agent = relationship("Agent", foreign_keys=[created_by_agent_id])
