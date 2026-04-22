import logging
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from app.modules.task_board.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)

class TaskBoardAgentScheduler:
    """定时轮询未认领任务的调度器"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def poll_unclaimed_tasks(self, limit: int = 10) -> List[Task]:
        """获取未认领的任务列表"""
        return self.db.query(Task).filter(
            Task.status == TaskStatus.UNCLAIMED
        ).order_by(
            Task.priority.desc(),
            Task.created_at.asc()
        ).limit(limit).all()
    
    def get_pending_tasks_for_agent(self, agent_id: str, limit: int = 10) -> List[Task]:
        """获取分配给指定 Agent 的待处理任务"""
        return self.db.query(Task).filter(
            Task.assigned_to_agent_id == agent_id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.UNCLAIMED])
        ).order_by(
            Task.priority.desc(),
            Task.due_date.asc()
        ).limit(limit).all()
    
    def notify_agent(self, agent_id: str, task: Task) -> bool:
        """
        通知 Agent 有新任务
        这里可以接入 Agent 的消息通知系统
        目前只是记录日志
        """
        logger.info(f"[TaskBoard] Notifying agent {agent_id} about task {task.id}: {task.title}")
        # TODO: 接入 Agent 消息通知系统
        return True
    
    def run_polling_cycle(self) -> dict:
        """执行一次轮询周期"""
        unclaimed_tasks = self.poll_unclaimed_tasks()
        notified_count = 0
        
        for task in unclaimed_tasks:
            if task.assigned_to_agent_id:
                self.notify_agent(task.assigned_to_agent_id, task)
                notified_count += 1
        
        return {
            "polled_at": datetime.now(timezone.utc).isoformat(),
            "unclaimed_count": len(unclaimed_tasks),
            "notified_count": notified_count,
        }