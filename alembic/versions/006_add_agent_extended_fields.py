"""Add capabilities, self_introduction, and work_preferences to agents

Revision ID: 006_add_agent_extended_fields
Revises: 005_add_task_board
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR, JSON, TEXT

# revision identifiers, used by Alembic.
revision: str = '006_add_agent_extended_fields'
down_revision: Union[str, None] = '005_add_task_board'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agents', sa.Column('capabilities', TEXT, nullable=True))
    op.add_column('agents', sa.Column('self_introduction', TEXT, nullable=True))
    op.add_column('agents', sa.Column('work_preferences', JSON, nullable=True))


def downgrade() -> None:
    op.drop_column('agents', 'work_preferences')
    op.drop_column('agents', 'self_introduction')
    op.drop_column('agents', 'capabilities')
