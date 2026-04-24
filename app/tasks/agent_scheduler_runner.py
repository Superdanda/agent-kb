import logging
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.repositories.agent_scheduler_repo import AgentSchedulerRepository
from app.models.agent_scheduler import SchedulerStatus
from app.services.scheduler_dispatch import dispatch_scheduler

logger = logging.getLogger(__name__)


def execute_due_schedulers():
    """
    Poll for due schedulers and execute them.
    This function is called every minute by the BackgroundScheduler.
    Each due scheduler is executed in-process (for simplicity).
    For heavy workloads, consider offloading to a worker queue.
    """
    db = SessionLocal()
    try:
        repo = AgentSchedulerRepository(db)
        due_schedulers = repo.get_due_tasks(limit=50)

        if not due_schedulers:
            logger.debug("No due schedulers found")
            return

        logger.info(f"Found {len(due_schedulers)} due schedulers")
        for scheduler in due_schedulers:
            _execute_scheduler(db, repo, scheduler)

    except Exception as e:
        logger.error(f"Error polling due schedulers: {e}")
        raise
    finally:
        db.close()


def _execute_scheduler(db, repo, scheduler):
    """Execute a single scheduler task."""
    started_at = datetime.now(timezone.utc)

    repo.update_status(
        scheduler.id,
        status=SchedulerStatus.RUNNING.value,
        last_run_at=started_at,
    )

    try:
        logger.info(f"Executing scheduler {scheduler.id} ({scheduler.task_name})")

        context = {
            "scheduler_id": scheduler.id,
            "agent_id": scheduler.agent_id,
            "task_name": scheduler.task_name,
            "task_type": scheduler.task_type,
        }

        result = _dispatch_task(db, scheduler, context)

        finished_at = datetime.now(timezone.utc)
        status = SchedulerStatus.SUCCESS.value
        result_text = result.message
        repo.update_status(
            scheduler.id,
            status=status,
            result=result_text,
            last_run_at=started_at,
        )
        log = repo.create_execution_log(
            scheduler_id=scheduler.id,
            started_at=started_at,
            status=status,
            result=result_text,
        )
        repo.finish_execution_log(log.id, finished_at, status, result_text)
        logger.info(f"Scheduler {scheduler.id} completed successfully: {result_text}")

    except Exception as e:
        finished_at = datetime.now(timezone.utc)
        error_msg = str(e)
        logger.error(f"Scheduler {scheduler.id} failed: {error_msg}")

        repo.update_status(
            scheduler.id,
            status=SchedulerStatus.FAILED.value,
            result=f"Error: {error_msg}",
        )
        log = repo.create_execution_log(
            scheduler_id=scheduler.id,
            started_at=started_at,
            status=SchedulerStatus.FAILED.value,
            result=error_msg,
        )
        repo.finish_execution_log(log.id, finished_at, SchedulerStatus.FAILED.value, error_msg)


def _dispatch_task(db, scheduler, context: dict):
    """Dispatch a scheduler through the registered dispatch handler."""
    logger.info(
        "Dispatching scheduler task '%s' (type=%s) with context: %s",
        scheduler.task_name,
        scheduler.task_type,
        context,
    )
    return dispatch_scheduler(db, scheduler, context)
