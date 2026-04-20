import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, CHAR, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class ApiNonce(Base):
    __tablename__ = "api_nonces"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    nonce = Column(String(128), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    agent = relationship("Agent", back_populates="api_nonces")

    __table_args__ = (
        Index("idx_api_nonces_expires", "expires_at"),
    )
