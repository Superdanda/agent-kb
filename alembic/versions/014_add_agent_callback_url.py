"""Add agent callback URL and type

Revision ID: 014_add_agent_callback_url
Revises: 013_add_admin_user_profile_fields
Create Date: 2026-04-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014_add_agent_callback_url"
down_revision: Union[str, None] = "013_add_admin_user_profile_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("callback_url", sa.String(1024), nullable=True))
    op.add_column("agents", sa.Column("agent_type", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "agent_type")
    op.drop_column("agents", "callback_url")
