"""
检查所有 Agent 的心跳状态，将长期未心跳的 Agent 标记为 INACTIVE。
"""
import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.agent import Agent, AgentStatus

logger = logging.getLogger(__name__)

# 超过这个时间未心跳则标记为 INACTIVE
HEARTBEAT_TIMEOUT_SECONDS = 120  # 2 分钟


def run_heartbeat_check() -> None:
    """
    每分钟运行一次，遍历所有 ACTIVE Agent：
    - 如果 (now - last_seen_at) > HEARTBEAT_TIMEOUT_SECONDS → 设为 INACTIVE
    - 如果 last_seen_at 为空且创建超过 5 分钟 → 设为 INACTIVE
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)

    db: Session = SessionLocal()
    try:
        # 找出所有应该被降级的 Agent
        candidates = db.query(Agent).filter(
            Agent.status == AgentStatus.ACTIVE,
        )

        marked_inactive = 0
        now = datetime.now(timezone.utc)
        for agent in candidates.all():
            if agent.last_seen_at is None:
                # 从未发过心跳，且创建超过 5 分钟 → 降级
                # created_at 是 naive datetime，转换为 aware
                created_at = agent.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if created_at < now - timedelta(minutes=5):
                    agent.status = AgentStatus.INACTIVE
                    marked_inactive += 1
                    logger.info(f"Agent {agent.agent_code} ({agent.id}) marked INACTIVE: never seen heartbeat")
            last_seen = agent.last_seen_at
            if last_seen is None:
                # 从未发过心跳，且创建超过 5 分钟 → 降级
                created_at = agent.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                if created_at < now - timedelta(minutes=5):
                    agent.status = AgentStatus.INACTIVE
                    marked_inactive += 1
                    logger.info(f"Agent {agent.agent_code} ({agent.id}) marked INACTIVE: never seen heartbeat")
            else:
                # ensure aware
                if last_seen.tzinfo is None:
                    last_seen = last_seen.replace(tzinfo=timezone.utc)
                if last_seen < cutoff:
                    agent.status = AgentStatus.INACTIVE
                    marked_inactive += 1
                    logger.info(f"Agent {agent.agent_code} ({agent.id}) marked INACTIVE: last_seen={last_seen.isoformat()}")

        if marked_inactive > 0:
            db.commit()
            logger.info(f"Heartbeat check: marked {marked_inactive} agent(s) as INACTIVE")
        else:
            logger.debug("Heartbeat check: all agents are healthy")
    except Exception as e:
        db.rollback()
        logger.error(f"Heartbeat check error: {e}")
    finally:
        db.close()
