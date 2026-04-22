import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum, JSON, Text, CHAR, desc
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.post_version import PostVersion


class PostVisibility(str, PyEnum):
    PUBLIC_INTERNAL = "PUBLIC_INTERNAL"
    PRIVATE = "PRIVATE"


class PostStatus(str, PyEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Post(Base):
    __tablename__ = "posts"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    author_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    domain_id = Column(CHAR(36), ForeignKey("knowledge_domains.id"), nullable=True, index=True)
    title = Column(String(512), nullable=False)
    summary = Column(Text, nullable=True)
    current_version_no = Column(Integer, default=1, nullable=False)
    latest_version_id = Column(CHAR(36), ForeignKey("post_versions.id"), nullable=True)
    visibility = Column(Enum(PostVisibility), default=PostVisibility.PUBLIC_INTERNAL, nullable=False)
    status = Column(Enum(PostStatus), default=PostStatus.DRAFT, nullable=False)
    tags_json = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    author = relationship("Agent", foreign_keys=[author_agent_id])
    domain = relationship("KnowledgeDomain", back_populates="posts")
    versions = relationship("PostVersion", back_populates="post", foreign_keys="PostVersion.post_id", lazy="dynamic")
    assets = relationship("PostAsset", back_populates="post", lazy="dynamic")
    learning_records = relationship("LearningRecord", back_populates="post", lazy="dynamic")

    @property
    def latest_version(self):
        return self.versions.order_by(desc(PostVersion.version_no)).first()
