"""Add last_seen_at to agents table

Revision ID: 007_add_agent_last_seen_at
Revises: 006_add_agent_extended_fields
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DATETIME

# revision identifiers, used by Alembic.
revision: str = '007_add_agent_last_seen_at'
down_revision: Union[str, None] = '006_add_agent_extended_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agents', sa.Column('last_seen_at', DATETIME(fsp=6), nullable=True))


def downgrade() -> None:
    op.drop_column('agents', 'last_seen_at')
