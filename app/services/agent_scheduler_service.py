import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from croniter import croniter
from sqlalchemy.orm import Session

from app.repositories.agent_scheduler_repo import AgentSchedulerRepository
from app.models.agent_scheduler import (
    AgentScheduler, SchedulerStatus, SchedulerTaskType, SchedulerExecutionLog
)
from app.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


def _scheduler_to_dict(s: AgentScheduler, agent_name: str = None) -> dict:
    return {
        "id": s.id,
        "agent_id": s.agent_id,
        "agent_name": agent_name or (s.agent.name if s.agent else s.agent_id),
        "task_name": s.task_name,
        "task_type": s.task_type,
        "cron_expression": s.cron_expression,
        "interval_seconds": s.interval_seconds,
        "run_at": s.run_at.isoformat() if s.run_at else None,
        "enabled": s.enabled,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "status": s.status,
        "result": s.result,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _execution_log_to_dict(log: SchedulerExecutionLog) -> dict:
    duration_seconds = None
    if log.started_at and log.finished_at:
        duration_seconds = (log.finished_at - log.started_at).total_seconds()
    return {
        "id": log.id,
        "scheduler_id": log.scheduler_id,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "finished_at": log.finished_at.isoformat() if log.finished_at else None,
        "duration_seconds": duration_seconds,
        "status": log.status,
        "result": log.result,
    }


class AgentSchedulerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AgentSchedulerRepository(db)

    def create_scheduler(
        self,
        agent_id: str,
        task_name: str,
        task_type: str = SchedulerTaskType.PERIODIC.value,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        run_at: Optional[datetime] = None,
        enabled: bool = True,
    ) -> dict:
        scheduler = self.repo.create(
            agent_id=agent_id,
            task_name=task_name,
            task_type=task_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            run_at=run_at,
            enabled=enabled,
        )
        # Calculate initial next_run_at
        scheduler = self._recalculate_next_run(scheduler)
        return _scheduler_to_dict(scheduler)

    def get_scheduler(self, scheduler_id: str) -> dict:
        scheduler = self.repo.get_by_id(scheduler_id)
        if not scheduler:
            raise ResourceNotFoundError(f"Scheduler {scheduler_id} not found")
        return _scheduler_to_dict(scheduler)

    def list_schedulers(
        self,
        status: Optional[str] = None,
        enabled: Optional[bool] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        items, total = self.repo.list_all(
            status=status,
            enabled=enabled,
            agent_id=agent_id,
            limit=limit,
            offset=offset,
        )
        return {
            "items": [_scheduler_to_dict(s) for s in items],
            "total": total,
        }

    def list_by_agent(
        self,
        agent_id: str,
        enabled: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        items, total = self.repo.list_by_agent(
            agent_id=agent_id,
            enabled=enabled,
            limit=limit,
            offset=offset,
        )
        return {
            "items": [_scheduler_to_dict(s) for s in items],
            "total": total,
        }

    def update_scheduler(
        self,
        scheduler_id: str,
        task_name: Optional[str] = None,
        task_type: Optional[str] = None,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        run_at: Optional[datetime] = None,
        enabled: Optional[bool] = None,
    ) -> dict:
        scheduler = self.repo.update(
            scheduler_id=scheduler_id,
            task_name=task_name,
            task_type=task_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            run_at=run_at,
            enabled=enabled,
        )
        if not scheduler:
            raise ResourceNotFoundError(f"Scheduler {scheduler_id} not found")

        # Recalculate next_run_at after update
        scheduler = self._recalculate_next_run(scheduler)
        return _scheduler_to_dict(scheduler)

    def delete_scheduler(self, scheduler_id: str) -> bool:
        deleted = self.repo.delete(scheduler_id)
        if not deleted:
            raise ResourceNotFoundError(f"Scheduler {scheduler_id} not found")
        return True

    def toggle_scheduler(self, scheduler_id: str, enabled: bool) -> dict:
        scheduler = self.repo.update(scheduler_id=scheduler_id, enabled=enabled)
        if not scheduler:
            raise ResourceNotFoundError(f"Scheduler {scheduler_id} not found")
        return _scheduler_to_dict(scheduler)

    def get_execution_logs(
        self,
        scheduler_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        # Verify scheduler exists
        scheduler = self.repo.get_by_id(scheduler_id)
        if not scheduler:
            raise ResourceNotFoundError(f"Scheduler {scheduler_id} not found")

        items, total = self.repo.get_execution_logs(
            scheduler_id=scheduler_id,
            limit=limit,
            offset=offset,
        )
        return {
            "items": [_execution_log_to_dict(log) for log in items],
            "total": total,
        }

    def _recalculate_next_run(self, scheduler: AgentScheduler) -> AgentScheduler:
        """Recalculate and persist the next_run_at based on task_type."""
        now = datetime.now(timezone.utc)
        next_run = None

        if scheduler.task_type == SchedulerTaskType.PERIODIC.value and scheduler.interval_seconds:
            next_run = now.replace(microsecond=0)
            # For periodic tasks, next_run_at is updated after each execution
        elif scheduler.task_type == SchedulerTaskType.CRON.value and scheduler.cron_expression:
            try:
                cron = croniter(scheduler.cron_expression, now)
                next_run = cron.get_next(datetime)
            except Exception as e:
                logger.warning(f"Invalid cron expression '{scheduler.cron_expression}': {e}")
        elif scheduler.task_type == SchedulerTaskType.ONEDAY.value and scheduler.run_at:
            if scheduler.run_at > now:
                next_run = scheduler.run_at
            # If run_at is in the past, leave next_run_at None (won't run again)

        if next_run is not None:
            scheduler = self.repo.update_status(
                scheduler.id,
                status=scheduler.status,
                next_run_at=next_run,
            )

        return scheduler

    def calculate_next_run(
        self,
        task_type: str,
        cron_expression: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        run_at: Optional[datetime] = None,
        from_time: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """Calculate next run time given task parameters."""
        now = from_time or datetime.now(timezone.utc)

        if task_type == SchedulerTaskType.PERIODIC.value and interval_seconds:
            return now.replace(microsecond=0)
        elif task_type == SchedulerTaskType.CRON.value and cron_expression:
            try:
                cron = croniter(cron_expression, now)
                return cron.get_next(datetime)
            except Exception:
                return None
        elif task_type == SchedulerTaskType.ONEDAY.value and run_at:
            return run_at if run_at > now else None

        return None

    def record_execution(
        self,
        scheduler_id: str,
        status: str,
        result: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
    ) -> dict:
        """Record an execution (for callback from scheduler runner)."""
        now = datetime.now(timezone.utc)
        start_time = started_at or now

        # Create execution log
        log = self.repo.create_execution_log(
            scheduler_id=scheduler_id,
            started_at=start_time,
            status=status,
            result=result,
        )

        # Update scheduler status
        next_run = None
        if status in (SchedulerStatus.SUCCESS.value,):
            scheduler = self.repo.get_by_id(scheduler_id)
            if scheduler:
                next_run = self.calculate_next_run(
                    task_type=scheduler.task_type,
                    cron_expression=scheduler.cron_expression,
                    interval_seconds=scheduler.interval_seconds,
                    run_at=scheduler.run_at,
                    from_time=finished_at or now,
                )

        self.repo.update_status(
            scheduler_id=scheduler_id,
            status=status,
            result=result,
            last_run_at=start_time,
            next_run_at=next_run,
        )

        return _execution_log_to_dict(log)
