from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.api.schemas.agent_scheduler import (
    SchedulerCreate,
    SchedulerUpdate,
    SchedulerResponse,
    SchedulerListResponse,
    ExecutionLogResponse,
    ExecutionLogListResponse,
)
from app.services.agent_scheduler_service import AgentSchedulerService

router = APIRouter(prefix="/schedulers", tags=["schedulers"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SchedulerResponse)
def create_scheduler(
    data: SchedulerCreate,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AgentSchedulerService(db)
    return svc.create_scheduler(
        agent_id=agent_id,
        task_name=data.task_name,
        task_type=data.task_type,
        cron_expression=data.cron_expression,
        interval_seconds=data.interval_seconds,
        run_at=data.run_at,
        enabled=data.enabled,
    )


@router.get("", response_model=SchedulerListResponse)
def list_schedulers(
    status: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    current_agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AgentSchedulerService(db)
    return svc.list_schedulers(
        status=status,
        enabled=enabled,
        agent_id=agent_id,
        limit=limit,
        offset=offset,
    )


@router.get("/me", response_model=SchedulerListResponse)
def list_my_schedulers(
    enabled: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1),
    offset: int = Query(0, ge=0),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AgentSchedulerService(db)
    return svc.list_by_agent(
        agent_id=agent_id,
        enabled=enabled,
        limit=limit,
        offset=offset,
    )


@router.get("/{scheduler_id}", response_model=SchedulerResponse)
def get_scheduler(
    scheduler_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AgentSchedulerService(db)
    return svc.get_scheduler(scheduler_id)


@router.put("/{scheduler_id}", response_model=SchedulerResponse)
def update_scheduler(
    scheduler_id: str,
    data: SchedulerUpdate,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AgentSchedulerService(db)
    return svc.update_scheduler(
        scheduler_id=scheduler_id,
        task_name=data.task_name,
        task_type=data.task_type,
        cron_expression=data.cron_expression,
        interval_seconds=data.interval_seconds,
        run_at=data.run_at,
        enabled=data.enabled,
    )


@router.delete("/{scheduler_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduler(
    scheduler_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AgentSchedulerService(db)
    svc.delete_scheduler(scheduler_id)


@router.post("/{scheduler_id}/toggle", response_model=SchedulerResponse)
def toggle_scheduler(
    scheduler_id: str,
    enabled: bool = Query(..., description="True to enable, False to disable"),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AgentSchedulerService(db)
    return svc.toggle_scheduler(scheduler_id, enabled)


@router.get("/{scheduler_id}/logs", response_model=ExecutionLogListResponse)
def get_execution_logs(
    scheduler_id: str,
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    svc = AgentSchedulerService(db)
    return svc.get_execution_logs(
        scheduler_id=scheduler_id,
        limit=limit,
        offset=offset,
    )
