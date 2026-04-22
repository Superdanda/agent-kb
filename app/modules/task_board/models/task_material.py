import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, CHAR, Integer, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class MaterialType(str, PyEnum):
    DOCUMENT = "DOCUMENT"
    IMAGE = "IMAGE"
    LINK = "LINK"
    FILE = "FILE"
    REFERENCE = "REFERENCE"


class TaskMaterial(Base):
    __tablename__ = "task_materials"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(CHAR(36), ForeignKey("tasks.id"), nullable=False, index=True)
    material_type = Column(Enum(MaterialType), nullable=False)
    
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=True)
    url = Column(String(1024), nullable=True)
    file_path = Column(String(512), nullable=True)
    
    order_index = Column(Integer, default=0, nullable=False)
    is_result: bool = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="materials")
