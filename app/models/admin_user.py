import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, CHAR, Text
from app.core.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(CHAR(36), unique=True, nullable=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(128), nullable=True)
    avatar_object_key = Column(String(1024), nullable=True)
    avatar_url = Column(String(1024), nullable=True)
    bio = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(64), nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
