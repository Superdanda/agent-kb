import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class KnowledgeDomain(Base):
    __tablename__ = "knowledge_domains"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(64), nullable=True)  # emoji or font-awesome class
    color = Column(String(16), nullable=True)  # hex color for UI
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # relationship
    posts = relationship("Post", back_populates="domain", lazy="dynamic")
