from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.modules.task_board.models.task import TaskPriority, TaskDifficulty, TaskStatus


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    difficulty: Optional[TaskDifficulty] = None
    points: int = 0
    estimated_hours: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    difficulty: Optional[TaskDifficulty] = None
    status: Optional[TaskStatus] = None
    points: Optional[int] = None
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    due_date: Optional[datetime] = None
    assigned_to_agent_id: Optional[str] = None
    tags: Optional[List[str]] = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    created_by_agent_id: Optional[str] = None
    created_by_admin_uuid: Optional[str] = None
    assigned_to_agent_id: Optional[str] = None
    domain_id: Optional[str] = None
    priority: TaskPriority
    difficulty: Optional[TaskDifficulty] = None
    status: TaskStatus
    points: int
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    lease_token: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    lease_renewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
