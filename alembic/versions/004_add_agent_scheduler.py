"""Add agent_schedulers and scheduler_execution_logs tables

Revision ID: 004_add_agent_scheduler
Revises: 003_add_suggestions
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR

# revision identifiers, used by Alembic.
revision: str = '004_add_agent_scheduler'
down_revision: Union[str, None] = '003_add_suggestions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_schedulers table
    op.create_table(
        'agent_schedulers',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('task_name', sa.String(128), nullable=False),
        sa.Column('task_type', sa.String(32), nullable=False, server_default='periodic'),
        sa.Column('cron_expression', sa.String(128), nullable=True),
        sa.Column('interval_seconds', sa.Integer, nullable=True),
        sa.Column('run_at', sa.DateTime, nullable=True),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='1'),
        sa.Column('last_run_at', sa.DateTime, nullable=True),
        sa.Column('next_run_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(32), nullable=False, server_default='IDLE'),
        sa.Column('result', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_agent_schedulers_agent_id', 'agent_schedulers', ['agent_id'])
    op.create_index('ix_agent_schedulers_status', 'agent_schedulers', ['status'])
    op.create_index('ix_agent_schedulers_enabled', 'agent_schedulers', ['enabled'])
    op.create_index('ix_agent_schedulers_next_run_at', 'agent_schedulers', ['next_run_at'])

    # Create scheduler_execution_logs table
    op.create_table(
        'scheduler_execution_logs',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('scheduler_id', CHAR(36), sa.ForeignKey('agent_schedulers.id'), nullable=False),
        sa.Column('started_at', sa.DateTime, nullable=False),
        sa.Column('finished_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('result', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_scheduler_execution_logs_scheduler_id', 'scheduler_execution_logs', ['scheduler_id'])
    op.create_index('ix_scheduler_execution_logs_started_at', 'scheduler_execution_logs', ['started_at'])


def downgrade() -> None:
    op.drop_index('ix_scheduler_execution_logs_started_at', 'scheduler_execution_logs')
    op.drop_index('ix_scheduler_execution_logs_scheduler_id', 'scheduler_execution_logs')
    op.drop_table('scheduler_execution_logs')
    op.drop_index('ix_agent_schedulers_next_run_at', 'agent_schedulers')
    op.drop_index('ix_agent_schedulers_enabled', 'agent_schedulers')
    op.drop_index('ix_agent_schedulers_status', 'agent_schedulers')
    op.drop_index('ix_agent_schedulers_agent_id', 'agent_schedulers')
    op.drop_table('agent_schedulers')
