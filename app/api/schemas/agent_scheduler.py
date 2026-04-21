from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class SchedulerCreate(BaseModel):
    task_name: str = Field(..., max_length=128)
    task_type: str = Field(default="periodic", max_length=32)
    cron_expression: Optional[str] = Field(None, max_length=128)   # e.g., "0 * * * *"
    interval_seconds: Optional[int] = Field(None, ge=1)              # e.g., 3600
    run_at: Optional[datetime] = None                                  # For oneday type
    enabled: bool = True


class SchedulerUpdate(BaseModel):
    task_name: Optional[str] = Field(None, max_length=128)
    task_type: Optional[str] = Field(None, max_length=32)
    cron_expression: Optional[str] = Field(None, max_length=128)
    interval_seconds: Optional[int] = Field(None, ge=1)
    run_at: Optional[datetime] = None
    enabled: Optional[bool] = None


class SchedulerResponse(BaseModel):
    id: str
    agent_id: str
    agent_name: Optional[str] = None
    task_name: str
    task_type: str
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[datetime] = None
    enabled: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    status: str
    result: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SchedulerListResponse(BaseModel):
    items: List[SchedulerResponse]
    total: int


class ExecutionLogResponse(BaseModel):
    id: str
    scheduler_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    status: str
    result: Optional[str] = None

    model_config = {"from_attributes": True}


class ExecutionLogListResponse(BaseModel):
    items: List[ExecutionLogResponse]
    total: int
