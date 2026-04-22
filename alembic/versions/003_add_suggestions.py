"""Add suggestions table

Revision ID: 003_add_suggestions
Revises: 002_add_knowledge_domains
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR

# revision identifiers, used by Alembic.
revision: str = '003_add_suggestions'
down_revision: Union[str, None] = '002_add_knowledge_domains'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create suggestions table
    op.create_table(
        'suggestions',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('title', sa.String(256), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('category', sa.String(64), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='PENDING'),
        sa.Column('priority', sa.String(16), server_default='NORMAL'),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_suggestions_agent_id', 'suggestions', ['agent_id'])
    op.create_index('ix_suggestions_status', 'suggestions', ['status'])
    op.create_index('ix_suggestions_category', 'suggestions', ['category'])

    # Create suggestion_replies table
    op.create_table(
        'suggestion_replies',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('suggestion_id', CHAR(36), sa.ForeignKey('suggestions.id'), nullable=False),
        sa.Column('agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_suggestion_replies_suggestion_id', 'suggestion_replies', ['suggestion_id'])


def downgrade() -> None:
    op.drop_index('ix_suggestion_replies_suggestion_id', 'suggestion_replies')
    op.drop_table('suggestion_replies')
    op.drop_index('ix_suggestions_category', 'suggestions')
    op.drop_index('ix_suggestions_status', 'suggestions')
    op.drop_index('ix_suggestions_agent_id', 'suggestions')
    op.drop_table('suggestions')
