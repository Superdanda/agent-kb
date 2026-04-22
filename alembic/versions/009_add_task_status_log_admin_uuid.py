"""Add admin_uuid to task_status_logs

Revision ID: 009_add_task_status_log_admin_uuid
Revises: 008_add_admin_uuid
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR


revision: str = '009_add_task_status_log_admin_uuid'
down_revision: Union[str, None] = '008_add_admin_uuid'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('task_status_logs', sa.Column('admin_uuid', CHAR(36), nullable=True))
    # Make agent_id nullable so admin actions can use admin_uuid instead
    op.alter_column('task_status_logs', 'agent_id', existing_type=sa.CHAR(36), nullable=True)


def downgrade() -> None:
    op.alter_column('task_status_logs', 'agent_id', nullable=False)
    op.drop_column('task_status_logs', 'admin_uuid')
