import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=timezone.utc)


def init_scheduler() -> BackgroundScheduler:
    """Initialize and return the scheduler with all jobs."""
    
    from app.tasks.relearn_scan import run_relearn_scan
    from app.tasks.cleanup import run_cleanup_task
    
    # Run relearn scan every hour
    scheduler.add_job(
        run_relearn_scan,
        CronTrigger(minute=0),  # Every hour at minute 0
        id="relearn_scan",
        name="Scan posts for outdated learning records",
        replace_existing=True,
    )
    
    # Run cleanup every day at 3am
    scheduler.add_job(
        run_cleanup_task,
        CronTrigger(hour=3, minute=0),
        id="cleanup",
        name="Cleanup expired nonces and temp files",
        replace_existing=True,
    )
    
    # Poll and execute due agent schedulers every minute
    scheduler.add_job(
        run_agent_scheduler_poll,
        CronTrigger(second=0),  # Every minute at second 0
        id="agent_scheduler_poll",
        name="Poll and execute due agent schedulers",
        replace_existing=True,
    )

    # Check agent heartbeat status every minute
    from app.tasks.agent_heartbeat_check import run_heartbeat_check
    scheduler.add_job(
        run_heartbeat_check,
        CronTrigger(second=30),  # Every minute at second 30
        id="agent_heartbeat_check",
        name="Mark stale agents as INACTIVE",
        replace_existing=True,
    )
    
    logger.info(f"Scheduler initialized with {len(scheduler.get_jobs())} jobs")
    return scheduler


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")


def run_agent_scheduler_poll():
    """Poll for due agent schedulers and execute them."""
    from app.tasks.agent_scheduler_runner import execute_due_schedulers
    try:
        execute_due_schedulers()
    except Exception as e:
        logger.error(f"Agent scheduler poll error: {e}")

