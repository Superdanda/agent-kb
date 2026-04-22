import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Integer, CHAR, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class LeaderboardPeriod(str, PyEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    ALL_TIME = "ALL_TIME"


class Leaderboard(Base):
    __tablename__ = "leaderboards"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    
    period = Column(String(16), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    rank = Column(Integer, nullable=False)
    score = Column(Integer, default=0, nullable=False)
    tasks_completed = Column(Integer, default=0, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)
    avg_rating = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('agent_id', 'period', 'period_start', name='uq_leaderboard_unique'),
    )

    agent = relationship("Agent", foreign_keys=[agent_id])
