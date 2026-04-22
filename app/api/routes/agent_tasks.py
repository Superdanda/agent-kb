"""
Agent-facing API for heartbeat and task polling.
These endpoints are designed for Hermes Agents to interact with the platform
via scheduled tasks (cron jobs).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent, get_current_agent_for_heartbeat
from app.models.agent import Agent, AgentStatus
from app.models.credential import AgentCredential
from app.models.api_nonce import ApiNonce
from app.modules.task_board.models.task import Task, TaskStatus, TaskPriority
from app.modules.task_board.models.task_material import TaskMaterial
from app.modules.task_board.schemas.task import TaskResponse

router = APIRouter(prefix="/agent", tags=["agent-interaction"])


@router.post("/heartbeat")
def heartbeat(
    agent_id: str = Depends(get_current_agent_for_heartbeat),
    db: Session = Depends(get_db),
):
    """
    Agent heartbeat - updates last_seen_at and confirms agent is alive.
    Should be called every 30-60 seconds by the agent's scheduler.
    
    Returns agent info including any pending notifications.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Agent {agent_id} not found")

    agent.last_seen_at = datetime.now(timezone.utc)
    agent.status = AgentStatus.ACTIVE
    db.commit()

    # Count pending tasks assigned to this agent
    pending_count = db.query(Task).filter(
        Task.assigned_to_agent_id == agent_id,
        Task.status.in_([TaskStatus.PENDING, TaskStatus.UNCLAIMED, TaskStatus.IN_PROGRESS])
    ).count()

    return {
        "status": "ok",
        "agent_id": agent_id,
        "agent_code": agent.agent_code,
        "name": agent.name,
        "last_seen_at": agent.last_seen_at.isoformat(),
        "pending_tasks": pending_count,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/tasks/pending")
def get_pending_tasks(
    status_filter: Optional[str] = Query(
        default="PENDING,UNCLAIMED",
        description="Comma-separated task statuses to fetch (defaults to PENDING,UNCLAIMED)"
    ),
    limit: int = Query(default=10, ge=1, le=50, description="Max tasks to return"),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    Poll for pending tasks assigned to this agent.
    The agent should call this regularly (e.g., every 10-30 seconds).
    
    Returns tasks with their materials (file uploads) included.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Agent {agent_id} not found")

    # Update last_seen_at
    agent.last_seen_at = datetime.now(timezone.utc)
    agent.status = AgentStatus.ACTIVE
    db.commit()

    # Parse status filter
    status_values = []
    for s in status_filter.split(","):
        s = s.strip().upper()
        if s:
            try:
                status_values.append(TaskStatus(s))
            except ValueError:
                pass

    query = db.query(Task).filter(
        Task.assigned_to_agent_id == agent_id,
        Task.status.in_(status_values) if status_values else True
    ).order_by(
        Task.priority.desc(),
        Task.created_at.asc()
    ).limit(limit)

    tasks = query.all()

    result = []
    for task in tasks:
        # Get materials for this task
        materials = db.query(TaskMaterial).filter(TaskMaterial.task_id == task.id).all()
        
        task_data = TaskResponse.model_validate(task).model_dump()
        task_data["materials"] = [
            {
                "id": m.id,
                "filename": m.filename,
                "file_url": m.file_url,
                "file_type": m.file_type,
                "size_bytes": m.size_bytes,
            }
            for m in materials
        ]
        
        # Add creator agent name
        creator = db.query(Agent).filter(Agent.id == task.created_by_agent_id).first()
        task_data["created_by_name"] = creator.name if creator else task.created_by_agent_id
        
        result.append(task_data)

    return {
        "tasks": result,
        "count": len(result),
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/tasks/{task_id}/claim")
def claim_task(
    task_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    Agent claims a task, changing its status to IN_PROGRESS.
    Only works for PENDING or UNCLAIMED tasks assigned to this agent.
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.assigned_to_agent_id == agent_id
    ).first()
    
    if not task:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Task {task_id} not found or not assigned to you")

    if task.status not in [TaskStatus.PENDING, TaskStatus.UNCLAIMED]:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError(f"Task cannot be claimed in status: {task.status.value}")

    old_status = task.status
    task.status = TaskStatus.IN_PROGRESS
    task.started_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)

    return {
        "status": "claimed",
        "task_id": task_id,
        "new_status": task.status.value,
        "started_at": task.started_at.isoformat() if task.started_at else None,
    }


@router.post("/tasks/{task_id}/submit")
def submit_task_result(
    task_id: str,
    result_summary: str = Query(..., description="Summary of the task result"),
    actual_hours: Optional[int] = Query(None, description="Actual hours spent"),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    Agent submits task result, changing status to SUBMITTED.
    The task creator or admin will review and confirm/complete.
    """
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.assigned_to_agent_id == agent_id
    ).first()
    
    if not task:
        from app.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError(f"Task {task_id} not found or not assigned to you")

    if task.status != TaskStatus.IN_PROGRESS:
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError(f"Task must be IN_PROGRESS to submit, current: {task.status.value}")

    task.status = TaskStatus.SUBMITTED
    task.actual_hours = actual_hours
    task.updated_at = datetime.now(timezone.utc)
    
    # Store result in metadata
    import json
    metadata = task.metadata_json or {}
    metadata["result_summary"] = result_summary
    metadata["submitted_at"] = datetime.now(timezone.utc).isoformat()
    task.metadata_json = metadata
    
    db.commit()
    db.refresh(task)

    return {
        "status": "submitted",
        "task_id": task_id,
        "new_status": task.status.value,
    }
