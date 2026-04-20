import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Enum, Text, BigInteger, CHAR
from sqlalchemy.orm import relationship

from app.core.database import Base


class ScanStatus(str, PyEnum):
    QUARANTINED = "QUARANTINED"
    SAFE = "SAFE"
    REJECTED = "REJECTED"


class PostAsset(Base):
    __tablename__ = "post_assets"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    post_id = Column(CHAR(36), ForeignKey("posts.id"), nullable=False, index=True)
    version_id = Column(CHAR(36), ForeignKey("post_versions.id"), nullable=True, index=True)
    original_filename = Column(String(512), nullable=False)
    stored_object_key = Column(String(1024), nullable=False)
    file_ext = Column(String(32), nullable=True)
    file_size = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    mime_type = Column(String(128), nullable=True)
    detected_type = Column(String(64), nullable=True)
    scan_status = Column(Enum(ScanStatus), default=ScanStatus.QUARANTINED, nullable=False)
    reject_reason = Column(Text, nullable=True)
    created_by_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    post = relationship("Post", back_populates="assets")
    version = relationship("PostVersion")
    created_by_agent = relationship("Agent")
