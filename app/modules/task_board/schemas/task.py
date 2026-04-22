from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.task_board.models.task import TaskPriority, TaskDifficulty, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(..., max_length=512)
    description: Optional[str] = None
    assigned_to_agent_id: Optional[str] = None
    domain_id: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    difficulty: Optional[TaskDifficulty] = None
    points: int = 0
    estimated_hours: Optional[int] = None
    tags_json: Optional[list[str]] = None
    metadata_json: Optional[dict] = None
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=512)
    description: Optional[str] = None
    assigned_to_agent_id: Optional[str] = None
    domain_id: Optional[str] = None
    priority: Optional[TaskPriority] = None
    difficulty: Optional[TaskDifficulty] = None
    status: Optional[TaskStatus] = None
    points: Optional[int] = None
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    tags_json: Optional[list[str]] = None
    metadata_json: Optional[dict] = None
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    created_by_agent_id: str
    assigned_to_agent_id: Optional[str]
    domain_id: Optional[str]
    priority: TaskPriority
    difficulty: Optional[TaskDifficulty]
    status: TaskStatus
    points: int
    estimated_hours: Optional[int]
    actual_hours: Optional[int]
    tags_json: Optional[list[str]]
    metadata_json: Optional[dict]
    due_date: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
