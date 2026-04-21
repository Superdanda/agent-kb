"""Add task_board tables (tasks, task_materials, task_status_logs, task_ratings, leaderboards)

Revision ID: 005_add_task_board
Revises: 004_add_agent_scheduler
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR, JSON

# revision identifiers, used by Alembic.
revision: str = '005_add_task_board'
down_revision: Union[str, None] = '004_add_agent_scheduler'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tasks table
    op.create_table(
        'tasks',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('created_by_agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('assigned_to_agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=True),
        sa.Column('domain_id', CHAR(36), sa.ForeignKey('knowledge_domains.id'), nullable=True),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='taskpriority'), nullable=False),
        sa.Column('difficulty', sa.Enum('EASY', 'MEDIUM', 'HARD', 'EXPERT', name='taskdifficulty'), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'REVIEW', 'COMPLETED', 'CANCELLED', name='taskstatus'), nullable=False),
        sa.Column('points', sa.Integer, nullable=False, server_default='0'),
        sa.Column('estimated_hours', sa.Integer, nullable=True),
        sa.Column('actual_hours', sa.Integer, nullable=True),
        sa.Column('tags_json', JSON, nullable=True),
        sa.Column('metadata_json', JSON, nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_tasks_created_by_agent_id', 'tasks', ['created_by_agent_id'])
    op.create_index('ix_tasks_assigned_to_agent_id', 'tasks', ['assigned_to_agent_id'])
    op.create_index('ix_tasks_domain_id', 'tasks', ['domain_id'])
    op.create_index('ix_tasks_status', 'tasks', ['status'])

    # task_materials table
    op.create_table(
        'task_materials',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('task_id', CHAR(36), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('material_type', sa.Enum('DOCUMENT', 'IMAGE', 'LINK', 'FILE', 'REFERENCE', name='materialtype'), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('file_path', sa.String(512), nullable=True),
        sa.Column('order_index', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_task_materials_task_id', 'task_materials', ['task_id'])

    # task_status_logs table
    op.create_table(
        'task_status_logs',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('task_id', CHAR(36), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('from_status', sa.String(32), nullable=True),
        sa.Column('to_status', sa.String(32), nullable=False),
        sa.Column('change_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_task_status_logs_task_id', 'task_status_logs', ['task_id'])
    op.create_index('ix_task_status_logs_agent_id', 'task_status_logs', ['agent_id'])

    # task_ratings table
    op.create_table(
        'task_ratings',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('task_id', CHAR(36), sa.ForeignKey('tasks.id'), nullable=False),
        sa.Column('rater_agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('rated_agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('dimension', sa.String(32), nullable=False),
        sa.Column('score', sa.Integer, nullable=False),
        sa.Column('comment', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_task_ratings_task_id', 'task_ratings', ['task_id'])
    op.create_index('ix_task_ratings_rater_agent_id', 'task_ratings', ['rater_agent_id'])
    op.create_index('ix_task_ratings_rated_agent_id', 'task_ratings', ['rated_agent_id'])
    op.create_index('idx_task_ratings_unique', 'task_ratings', ['task_id', 'rater_agent_id', 'rated_agent_id', 'dimension'], unique=True)

    # leaderboards table
    op.create_table(
        'leaderboards',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('period', sa.String(16), nullable=False),
        sa.Column('period_start', sa.DateTime, nullable=False),
        sa.Column('period_end', sa.DateTime, nullable=False),
        sa.Column('rank', sa.Integer, nullable=False),
        sa.Column('score', sa.Integer, nullable=False, server_default='0'),
        sa.Column('tasks_completed', sa.Integer, nullable=False, server_default='0'),
        sa.Column('total_points', sa.Integer, nullable=False, server_default='0'),
        sa.Column('avg_rating', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_leaderboards_agent_id', 'leaderboards', ['agent_id'])
    op.create_index('idx_leaderboards_unique', 'leaderboards', ['agent_id', 'period', 'period_start'], unique=True)


def downgrade() -> None:
    op.drop_table('leaderboards')
    op.drop_table('task_ratings')
    op.drop_table('task_status_logs')
    op.drop_table('task_materials')
    op.drop_table('tasks')
