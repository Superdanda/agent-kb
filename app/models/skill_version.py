import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base


class SkillVersionStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    skill_id = Column(CHAR(36), ForeignKey("skills.id"), nullable=False, index=True)
    version = Column(String(64), nullable=False)
    summary_snapshot = Column(Text, nullable=True)
    tags_snapshot = Column(JSON, nullable=False, default=list)
    release_note = Column(Text, nullable=True)
    package_filename = Column(String(512), nullable=False)
    stored_object_key = Column(String(1024), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    mime_type = Column(String(128), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_by_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=True, index=True)
    created_by_admin_uuid = Column(CHAR(36), nullable=True, index=True)
    status = Column(Enum(SkillVersionStatus), nullable=False, default=SkillVersionStatus.ACTIVE)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    skill = relationship("Skill", back_populates="versions", foreign_keys=[skill_id])
    created_by_agent = relationship("Agent", foreign_keys=[created_by_agent_id])
