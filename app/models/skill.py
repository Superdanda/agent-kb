import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import CHAR

from app.core.database import Base


class SkillStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    HIDDEN = "HIDDEN"


class Skill(Base):
    __tablename__ = "skills"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(128), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    summary = Column(Text, nullable=True)
    tags_json = Column(JSON, nullable=False, default=list)
    current_version_id = Column(
        CHAR(36),
        ForeignKey("skill_versions.id", use_alter=True, name="fk_skills_current_version_id"),
        nullable=True,
    )
    uploader_agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=True, index=True)
    uploader_admin_uuid = Column(CHAR(36), nullable=True, index=True)
    is_recommended = Column(Boolean, nullable=False, default=False)
    is_important = Column(Boolean, nullable=False, default=False)
    is_official = Column(Boolean, nullable=False, default=False)
    status = Column(Enum(SkillStatus), nullable=False, default=SkillStatus.ACTIVE)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    uploader_agent = relationship("Agent", foreign_keys=[uploader_agent_id])
    versions = relationship(
        "SkillVersion",
        back_populates="skill",
        foreign_keys="SkillVersion.skill_id",
    )
