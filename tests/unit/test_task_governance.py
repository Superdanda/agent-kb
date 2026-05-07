from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.exceptions import PermissionDeniedError
from app.models import Agent
from app.modules.task_board.models.task import TaskStatus
from app.modules.task_board.models.task_material import MaterialType
from app.modules.task_board.services.material_service import MaterialService
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


def test_available_tasks_include_current_agent_in_progress(db):
    agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    db.add(agent)
    db.commit()

    task = TaskService(db).create_task(title="Work item")
    claimed = TaskService(db).claim_task(task.id, agent.id)

    tasks = TaskService(db).list_available_tasks(agent.id)

    assert [item.id for item in tasks] == [claimed.id]


def test_unassigned_task_is_visible_to_all_agents_until_claimed(db):
    agent_1 = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    agent_2 = Agent(id="agent-2", agent_code="agent-2", name="Agent 2")
    db.add_all([agent_1, agent_2])
    db.commit()

    task = TaskService(db).create_task(title="Open work item")

    assert [item.id for item in TaskService(db).list_available_tasks(agent_1.id)] == [task.id]
    assert [item.id for item in TaskService(db).list_available_tasks(agent_2.id)] == [task.id]

    claimed = TaskService(db).claim_task(task.id, agent_1.id)

    assert claimed.assigned_to_agent_id == agent_1.id
    assert [item.id for item in TaskService(db).list_available_tasks(agent_1.id)] == [task.id]
    assert TaskService(db).list_available_tasks(agent_2.id) == []


def test_submit_marks_result_materials(db):
    agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    db.add(agent)
    db.commit()

    task = TaskService(db).create_task(title="Work item")
    claimed = TaskService(db).claim_task(task.id, agent.id)
    material = MaterialService(db).create_material(
        task_id=claimed.id,
        material_type=MaterialType.FILE,
        title="result.zip",
        file_path="task_materials/result.zip",
    )

    TaskService(db).submit_task_result(
        task_id=claimed.id,
        agent_id=agent.id,
        result_summary="done",
        lease_token=claimed.lease_token,
        idempotency_key="submit-1",
        result_material_ids=[material.id],
        require_lease=True,
    )
    db.refresh(material)

    assert material.is_result is True


def test_reject_reissues_lease_and_records_reason(db):
    agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    db.add(agent)
    db.commit()

    task = TaskService(db).create_task(title="Work item")
    claimed = TaskService(db).claim_task(task.id, agent.id)
    old_token = claimed.lease_token
    submitted = TaskService(db).submit_task_result(
        task_id=claimed.id,
        agent_id=agent.id,
        result_summary="done",
        lease_token=old_token,
        idempotency_key="submit-1",
        require_lease=True,
    )

    rejected = TaskService(db).reject_task(
        task_id=submitted.id,
        reviewer_admin_uuid="admin-1",
        reason="Missing references; please add sources.",
    )

    assert rejected.status == TaskStatus.IN_PROGRESS
    assert rejected.assigned_to_agent_id == agent.id
    assert rejected.lease_token
    assert rejected.lease_token != old_token
    assert rejected.lease_expires_at is not None
    assert rejected.metadata_json["reject_reason"] == "Missing references; please add sources."


def test_admin_reset_to_unclaimed_clears_assignment_and_lease(db):
    agent = Agent(id="agent-1", agent_code="agent-1", name="Agent 1")
    db.add(agent)
    db.commit()

    task = TaskService(db).create_task(title="Work item")
    claimed = TaskService(db).claim_task(task.id, agent.id)

    reset = TaskService(db).reset_task_to_unclaimed(
        task_id=claimed.id,
        admin_uuid="admin-1",
        reason="Lease is missing; reopen for claim.",
    )

    assert reset.status == TaskStatus.UNCLAIMED
    assert reset.assigned_to_agent_id is None
    assert reset.lease_token is None
    assert reset.metadata_json["admin_reset_reason"] == "Lease is missing; reopen for claim."
