import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, CHAR, Boolean, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class SchedulerTaskType(str, PyEnum):
    PERIODIC = "periodic"       # Run at fixed interval
    ONEDAY = "oneday"           # Run once at specific time
    CRON = "cron"               # Run based on cron expression


class SchedulerStatus(str, PyEnum):
    IDLE = "IDLE"               # Not running
    RUNNING = "RUNNING"         # Currently executing
    SUCCESS = "SUCCESS"         # Last run succeeded
    FAILED = "FAILED"           # Last run failed
    DISABLED = "DISABLED"       # Manually disabled


class AgentScheduler(Base):
    __tablename__ = "agent_schedulers"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(CHAR(36), ForeignKey("agents.id"), nullable=False, index=True)
    task_name = Column(String(128), nullable=False)
    task_type = Column(String(32), nullable=False, default=SchedulerTaskType.PERIODIC.value)
    cron_expression = Column(String(128), nullable=True)      # For CRON type, e.g., "0 * * * *"
    interval_seconds = Column(Integer, nullable=True)          # For PERIODIC type
    run_at = Column(DateTime, nullable=True)                    # For ONEDAY type
    enabled = Column(Boolean, default=True, nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default=SchedulerStatus.IDLE.value)
    result = Column(Text, nullable=True)                        # Last execution result/error
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    agent = relationship("Agent", foreign_keys=[agent_id])


class SchedulerExecutionLog(Base):
    __tablename__ = "scheduler_execution_logs"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheduler_id = Column(CHAR(36), ForeignKey("agent_schedulers.id"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False)                 # SUCCESS, FAILED
    result = Column(Text, nullable=True)                        # Execution result or error message
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    scheduler = relationship("AgentScheduler", foreign_keys=[scheduler_id])
