from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.exceptions import PermissionDeniedError
from app.models import Agent
from app.modules.task_board.models.task import TaskStatus
from app.modules.task_board.services.task_service import TaskService


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_claim_creates_task_lease(db):
    agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    db.add(agent)
    db.commit()

    task = TaskService(db).create_task(title="Work item")
    claimed = TaskService(db).claim_task(task.id, agent.id)

    assert claimed.status == TaskStatus.IN_PROGRESS
    assert claimed.assigned_to_agent_id == agent.id
    assert claimed.lease_token
    assert claimed.lease_expires_at is not None


def test_submit_requires_matching_active_lease_when_enforced(db):
    agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    db.add(agent)
    db.commit()

    task = TaskService(db).create_task(title="Work item")
    claimed = TaskService(db).claim_task(task.id, agent.id)

    with pytest.raises(PermissionDeniedError):
        TaskService(db).submit_task_result(
            task_id=claimed.id,
            agent_id=agent.id,
            result_summary="done",
            lease_token="wrong",
            idempotency_key="submit-1",
            require_lease=True,
        )


def test_idempotent_submit_replays_existing_receipt(db):
    agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    db.add(agent)
    db.commit()

    task = TaskService(db).create_task(title="Work item")
    claimed = TaskService(db).claim_task(task.id, agent.id)
    first = TaskService(db).submit_task_result(
        task_id=claimed.id,
        agent_id=agent.id,
        result_summary="done",
        lease_token=claimed.lease_token,
        idempotency_key="submit-1",
        require_lease=True,
    )
    second = TaskService(db).submit_task_result(
        task_id=claimed.id,
        agent_id=agent.id,
        result_summary="done",
        lease_token=claimed.lease_token,
        idempotency_key="submit-1",
        require_lease=True,
    )

    assert first.id == second.id
    assert second.status == TaskStatus.SUBMITTED


def test_recover_expired_lease_returns_task_to_unclaimed(db):
    agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    db.add(agent)
    db.commit()

    task = TaskService(db).create_task(title="Work item")
    claimed = TaskService(db).claim_task(task.id, agent.id)
    claimed.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    recovered = TaskService(db).recover_expired_leases()
    db.refresh(claimed)

    assert recovered == 1
    assert claimed.status == TaskStatus.UNCLAIMED
    assert claimed.assigned_to_agent_id is None
    assert claimed.lease_token is None
