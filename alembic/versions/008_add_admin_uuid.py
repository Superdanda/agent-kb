"""Add UUID to admin_users table

Revision ID: 008_add_admin_uuid
Revises: 007_add_agent_last_seen_at
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR


revision: str = '008_add_admin_uuid'
down_revision: Union[str, None] = '007_add_agent_last_seen_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('admin_users', sa.Column('uuid', CHAR(36), nullable=True))


def downgrade() -> None:
    op.drop_column('admin_users', 'uuid')
