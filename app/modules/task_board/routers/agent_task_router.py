import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.middleware.auth import get_current_agent
from app.modules.task_board.models.task import Task, TaskStatus
from app.modules.task_board.models.task_status_log import TaskStatusLog
from app.modules.task_board.schemas.task import TaskResponse
from app.modules.task_board.services.leaderboard_service import LeaderboardService

router = APIRouter(prefix="/tasks", tags=["agent_tasks"])

@router.post("/{task_id}/claim")
def claim_task(
    task_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 承接任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status not in [TaskStatus.PENDING, TaskStatus.UNCLAIMED]:
        raise HTTPException(status_code=400, detail=f"Task cannot be claimed in status: {task.status}")
    
    if task.assigned_to_agent_id and task.assigned_to_agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Task already assigned to another agent")
    
    old_status = task.status
    task.status = TaskStatus.IN_PROGRESS
    task.assigned_to_agent_id = agent_id
    task.started_at = datetime.now(timezone.utc)
    
    # 记录状态变更
    log = TaskStatusLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        agent_id=agent_id,
        from_status=old_status.value if old_status else None,
        to_status=TaskStatus.IN_PROGRESS.value,
        change_reason="Agent claimed task",
    )
    db.add(log)
    db.commit()
    db.refresh(task)
    
    return TaskResponse.model_validate(task)

@router.post("/{task_id}/submit")
def submit_task(
    task_id: str,
    result_summary: str,
    material_ids: Optional[List[str]] = None,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 提交任务成果"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.assigned_to_agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Not assigned to this agent")
    
    if task.status != TaskStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail=f"Task cannot be submitted in status: {task.status}")
    
    old_status = task.status
    task.status = TaskStatus.SUBMITTED
    task.metadata_json = task.metadata_json or {}
    task.metadata_json["result_summary"] = result_summary
    task.metadata_json["result_material_ids"] = material_ids or []
    
    # 记录状态变更
    log = TaskStatusLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        agent_id=agent_id,
        from_status=old_status.value,
        to_status=TaskStatus.SUBMITTED.value,
        change_reason=result_summary,
    )
    db.add(log)
    db.commit()
    db.refresh(task)
    
    return TaskResponse.model_validate(task)

@router.post("/{task_id}/abandon")
def abandon_task(
    task_id: str,
    reason: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 放弃任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.assigned_to_agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Not assigned to this agent")
    
    if task.status not in [TaskStatus.IN_PROGRESS, TaskStatus.SUBMITTED]:
        raise HTTPException(status_code=400, detail=f"Task cannot be abandoned in status: {task.status}")
    
    old_status = task.status
    task.status = TaskStatus.CANCELLED
    task.assigned_to_agent_id = None
    task.metadata_json = task.metadata_json or {}
    task.metadata_json["abandon_reason"] = reason
    
    # 记录状态变更
    log = TaskStatusLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        agent_id=agent_id,
        from_status=old_status.value,
        to_status=TaskStatus.CANCELLED.value,
        change_reason=f"Abandoned: {reason}",
    )
    db.add(log)
    db.commit()
    db.refresh(task)
    
    return TaskResponse.model_validate(task)

@router.post("/{task_id}/confirm")
def confirm_task(
    task_id: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """确认任务完成（任务创建者或管理员操作）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail=f"Task cannot be confirmed in status: {task.status}")
    
    old_status = task.status
    task.status = TaskStatus.CONFIRMED
    task.completed_at = datetime.now(timezone.utc)
    
    # 记录状态变更
    log = TaskStatusLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        agent_id=agent_id,
        from_status=old_status.value,
        to_status=TaskStatus.CONFIRMED.value,
        change_reason="Task confirmed as completed",
    )
    db.add(log)
    db.commit()
    db.refresh(task)
    
    # 更新排行榜
    leaderboard_service = LeaderboardService(db)
    leaderboard_result = leaderboard_service.update_on_task_complete(task_id)
    
    return TaskResponse.model_validate(task)

@router.post("/{task_id}/reject")
def reject_task(
    task_id: str,
    reason: str,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """拒绝任务完成（打回给 Agent 重新处理）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status != TaskStatus.SUBMITTED:
        raise HTTPException(status_code=400, detail=f"Task cannot be rejected in status: {task.status}")
    
    old_status = task.status
    task.status = TaskStatus.IN_PROGRESS
    task.metadata_json = task.metadata_json or {}
    task.metadata_json["reject_reason"] = reason
    
    # 记录状态变更
    log = TaskStatusLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        agent_id=agent_id,
        from_status=old_status.value,
        to_status=TaskStatus.IN_PROGRESS.value,
        change_reason=f"Rejected: {reason}",
    )
    db.add(log)
    db.commit()
    db.refresh(task)
    
    return TaskResponse.model_validate(task)

@router.get("/agent/pending")
def get_agent_pending_tasks(
    limit: int = 10,
    agent_id: str = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """获取 Agent 的待处理任务"""
    tasks = db.query(Task).filter(
        Task.assigned_to_agent_id == agent_id,
        Task.status.in_([TaskStatus.PENDING, TaskStatus.UNCLAIMED, TaskStatus.IN_PROGRESS])
    ).order_by(
        Task.priority.desc(),
        Task.due_date.asc()
    ).limit(limit).all()
    
    return {
        "items": [TaskResponse.model_validate(t) for t in tasks],
        "total": len(tasks),
    }