"""Alter task created_by columns nullable and add created_by_admin_uuid

Revision ID: 010_alter_task_created_by_nullable
Revises: 009_add_task_status_log_admin_uuid
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR


revision: str = '010_alter_task_created_by_nullable'
down_revision: Union[str, None] = '009_add_task_status_log_admin_uuid'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make created_by_agent_id nullable
    op.alter_column('tasks', 'created_by_agent_id', existing_type=sa.CHAR(36), nullable=True)
    # Add created_by_admin_uuid column
    op.add_column('tasks', sa.Column('created_by_admin_uuid', CHAR(36), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'created_by_admin_uuid')
    op.alter_column('tasks', 'created_by_agent_id', nullable=False)
