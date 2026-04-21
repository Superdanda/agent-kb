import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.agent_scheduler import AgentScheduler, SchedulerExecutionLog, SchedulerStatus, SchedulerTaskType


class AgentSchedulerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        agent_id: str,
        task_name: str,
        task_type: str = SchedulerTaskType.PERIODIC.value,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        run_at: Optional[datetime] = None,
        enabled: bool = True,
    ) -> AgentScheduler:
        scheduler = AgentScheduler(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            task_name=task_name,
            task_type=task_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            run_at=run_at,
            enabled=enabled,
            status=SchedulerStatus.IDLE.value,
        )
        self.db.add(scheduler)
        self.db.commit()
        self.db.refresh(scheduler)
        return scheduler

    def get_by_id(self, scheduler_id: str) -> Optional[AgentScheduler]:
        return (
            self.db.query(AgentScheduler)
            .options(joinedload(AgentScheduler.agent))
            .filter(AgentScheduler.id == scheduler_id)
            .first()
        )

    def list_by_agent(
        self,
        agent_id: str,
        enabled: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AgentScheduler], int]:
        query = self.db.query(AgentScheduler).options(joinedload(AgentScheduler.agent))
        query = query.filter(AgentScheduler.agent_id == agent_id)

        if enabled is not None:
            query = query.filter(AgentScheduler.enabled == enabled)

        total = query.count()
        items = query.order_by(AgentScheduler.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def list_all(
        self,
        status: Optional[str] = None,
        enabled: Optional[bool] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[AgentScheduler], int]:
        query = self.db.query(AgentScheduler).options(joinedload(AgentScheduler.agent))

        if status:
            query = query.filter(AgentScheduler.status == status)
        if enabled is not None:
            query = query.filter(AgentScheduler.enabled == enabled)
        if agent_id:
            query = query.filter(AgentScheduler.agent_id == agent_id)

        total = query.count()
        items = query.order_by(AgentScheduler.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    def get_due_tasks(self, limit: int = 100) -> List[AgentScheduler]:
        """Get all enabled schedulers that are due to run."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(AgentScheduler)
            .options(joinedload(AgentScheduler.agent))
            .filter(
                AgentScheduler.enabled == True,
                or_(
                    AgentScheduler.next_run_at <= now,
                    AgentScheduler.next_run_at.is_(None),
                ),
            )
            .limit(limit)
            .all()
        )

    def update(
        self,
        scheduler_id: str,
        task_name: Optional[str] = None,
        task_type: Optional[str] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        run_at: Optional[datetime] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[AgentScheduler]:
        scheduler = self.db.query(AgentScheduler).filter(AgentScheduler.id == scheduler_id).first()
        if not scheduler:
            return None

        if task_name is not None:
            scheduler.task_name = task_name
        if task_type is not None:
            scheduler.task_type = task_type
        if cron_expression is not None:
            scheduler.cron_expression = cron_expression
        if interval_seconds is not None:
            scheduler.interval_seconds = interval_seconds
        if run_at is not None:
            scheduler.run_at = run_at
        if enabled is not None:
            scheduler.enabled = enabled

        scheduler.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(scheduler)
        return scheduler

    def update_status(
        self,
        scheduler_id: str,
        status: str,
        result: Optional[str] = None,
        last_run_at: Optional[datetime] = None,
        next_run_at: Optional[datetime] = None,
    ) -> Optional[AgentScheduler]:
        scheduler = self.db.query(AgentScheduler).filter(AgentScheduler.id == scheduler_id).first()
        if not scheduler:
            return None

        scheduler.status = status
        if result is not None:
            scheduler.result = result
        if last_run_at is not None:
            scheduler.last_run_at = last_run_at
        if next_run_at is not None:
            scheduler.next_run_at = next_run_at
        scheduler.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(scheduler)
        return scheduler

    def delete(self, scheduler_id: str) -> bool:
        scheduler = self.db.query(AgentScheduler).filter(AgentScheduler.id == scheduler_id).first()
        if not scheduler:
            return False
        self.db.delete(scheduler)
        self.db.commit()
        return True

    # Execution log methods
    def create_execution_log(
        self,
        scheduler_id: str,
        started_at: datetime,
        status: str = "RUNNING",
        result: Optional[str] = None,
    ) -> SchedulerExecutionLog:
        log = SchedulerExecutionLog(
            id=str(uuid.uuid4()),
            scheduler_id=scheduler_id,
            started_at=started_at,
            status=status,
            result=result,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def finish_execution_log(
        self,
        log_id: str,
        finished_at: datetime,
        status: str,
        result: Optional[str] = None,
    ) -> Optional[SchedulerExecutionLog]:
        log = self.db.query(SchedulerExecutionLog).filter(SchedulerExecutionLog.id == log_id).first()
        if not log:
            return None
        log.finished_at = finished_at
        log.status = status
        if result is not None:
            log.result = result
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_execution_logs(
        self,
        scheduler_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[SchedulerExecutionLog], int]:
        query = self.db.query(SchedulerExecutionLog).filter(SchedulerExecutionLog.scheduler_id == scheduler_id)
        total = query.count()
        items = query.order_by(SchedulerExecutionLog.started_at.desc()).offset(offset).limit(limit).all()
        return items, total
