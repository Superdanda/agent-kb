"""Add task leases and agent activity logs

Revision ID: 012_add_task_leases_and_activity_logs
Revises: 011_add_skills
Create Date: 2026-04-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR, JSON


revision: str = "012_add_task_leases_and_activity_logs"
down_revision: Union[str, None] = "011_add_skills"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("lease_token", sa.String(128), nullable=True))
    op.add_column("tasks", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("lease_renewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tasks_lease_token", "tasks", ["lease_token"])
    op.create_index("ix_tasks_lease_expires_at", "tasks", ["lease_expires_at"])

    op.create_table(
        "task_submission_receipts",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("task_id", CHAR(36), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("agent_id", CHAR(36), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("task_id", "agent_id", "idempotency_key", name="uq_task_submission_idempotency"),
    )
    op.create_index("ix_task_submission_receipts_task_id", "task_submission_receipts", ["task_id"])
    op.create_index("ix_task_submission_receipts_agent_id", "task_submission_receipts", ["agent_id"])

    op.create_table(
        "agent_activity_logs",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("agent_id", CHAR(36), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("object_type", sa.String(64), nullable=False),
        sa.Column("object_id", CHAR(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("detail_json", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_activity_logs_agent_id", "agent_activity_logs", ["agent_id"])
    op.create_index("ix_agent_activity_logs_action", "agent_activity_logs", ["action"])
    op.create_index("ix_agent_activity_logs_object_type", "agent_activity_logs", ["object_type"])
    op.create_index("ix_agent_activity_logs_object_id", "agent_activity_logs", ["object_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_activity_logs_object_id", table_name="agent_activity_logs")
    op.drop_index("ix_agent_activity_logs_object_type", table_name="agent_activity_logs")
    op.drop_index("ix_agent_activity_logs_action", table_name="agent_activity_logs")
    op.drop_index("ix_agent_activity_logs_agent_id", table_name="agent_activity_logs")
    op.drop_table("agent_activity_logs")

    op.drop_index("ix_task_submission_receipts_agent_id", table_name="task_submission_receipts")
    op.drop_index("ix_task_submission_receipts_task_id", table_name="task_submission_receipts")
    op.drop_table("task_submission_receipts")

    op.drop_index("ix_tasks_lease_expires_at", table_name="tasks")
    op.drop_index("ix_tasks_lease_token", table_name="tasks")
    op.drop_column("tasks", "lease_renewed_at")
    op.drop_column("tasks", "lease_expires_at")
    op.drop_column("tasks", "lease_token")
