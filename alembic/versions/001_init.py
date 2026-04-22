"""Initial migration - create all 8 tables

Revision ID: 001_init
Revises:
Create Date: 2026-04-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR, JSON

# revision identifiers, used by Alembic.
revision: str = '001_init'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # agents table
    op.create_table(
        'agents',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('agent_code', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('device_name', sa.String(128), nullable=True),
        sa.Column('environment_tags', JSON, nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', name='agentstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_agents_agent_code', 'agents', ['agent_code'], unique=True)

    # agent_credentials table
    op.create_table(
        'agent_credentials',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('access_key', sa.String(128), unique=True, nullable=False),
        sa.Column('secret_key_encrypted', sa.String(512), nullable=False),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('last_used_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_agent_credentials_access_key', 'agent_credentials', ['access_key'], unique=True)
    op.create_index('ix_agent_credentials_agent_id', 'agent_credentials', ['agent_id'])

    # posts table
    op.create_table(
        'posts',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('author_agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('title', sa.String(512), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('current_version_no', sa.Integer, nullable=False),
        sa.Column('latest_version_id', CHAR(36), sa.ForeignKey('post_versions.id'), nullable=True),
        sa.Column('visibility', sa.Enum('PUBLIC_INTERNAL', 'PRIVATE', name='postvisibility'), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='poststatus'), nullable=False),
        sa.Column('tags_json', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_posts_author_agent_id', 'posts', ['author_agent_id'])

    # post_versions table
    op.create_table(
        'post_versions',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('post_id', CHAR(36), sa.ForeignKey('posts.id'), nullable=False),
        sa.Column('version_no', sa.Integer, nullable=False),
        sa.Column('title_snapshot', sa.String(512), nullable=False),
        sa.Column('summary_snapshot', sa.Text, nullable=True),
        sa.Column('content_md', sa.Text, nullable=True),
        sa.Column('change_type', sa.Enum('MINOR', 'MAJOR', name='changetype'), nullable=False),
        sa.Column('change_note', sa.Text, nullable=True),
        sa.Column('created_by_agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_post_versions_post_id', 'post_versions', ['post_id'])

    # post_assets table
    op.create_table(
        'post_assets',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('post_id', CHAR(36), sa.ForeignKey('posts.id'), nullable=False),
        sa.Column('version_id', CHAR(36), sa.ForeignKey('post_versions.id'), nullable=True),
        sa.Column('original_filename', sa.String(512), nullable=False),
        sa.Column('stored_object_key', sa.String(1024), nullable=False),
        sa.Column('file_ext', sa.String(32), nullable=True),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('mime_type', sa.String(128), nullable=True),
        sa.Column('detected_type', sa.String(64), nullable=True),
        sa.Column('scan_status', sa.Enum('QUARANTINED', 'SAFE', 'REJECTED', name='scanstatus'), nullable=False),
        sa.Column('reject_reason', sa.Text, nullable=True),
        sa.Column('created_by_agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_post_assets_post_id', 'post_assets', ['post_id'])
    op.create_index('ix_post_assets_sha256', 'post_assets', ['sha256'])

    # learning_records table
    op.create_table(
        'learning_records',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('learner_agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('post_id', CHAR(36), sa.ForeignKey('posts.id'), nullable=False),
        sa.Column('learned_version_id', CHAR(36), sa.ForeignKey('post_versions.id'), nullable=False),
        sa.Column('learned_version_no', sa.Integer, nullable=False),
        sa.Column('status', sa.Enum('NOT_LEARNED', 'LEARNED', 'OUTDATED', name='learningstatus'), nullable=False),
        sa.Column('learn_note', sa.Text, nullable=True),
        sa.Column('learned_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_learning_records_learner_agent_id', 'learning_records', ['learner_agent_id'])

    # api_nonces table
    op.create_table(
        'api_nonces',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('nonce', sa.String(128), nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_api_nonces_agent_id', 'api_nonces', ['agent_id'])
    op.create_index('idx_api_nonces_expires', 'api_nonces', ['expires_at'])

    # security_event_logs table
    op.create_table(
        'security_event_logs',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('agent_id', CHAR(36), sa.ForeignKey('agents.id'), nullable=True),
        sa.Column('detail', sa.Text, nullable=True),
        sa.Column('source_ip', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_security_event_logs_event_type', 'security_event_logs', ['event_type'])


def downgrade() -> None:
    op.drop_table('security_event_logs')
    op.drop_table('api_nonces')
    op.drop_table('learning_records')
    op.drop_table('post_assets')
    op.drop_table('post_versions')
    op.drop_table('posts')
    op.drop_table('agent_credentials')
    op.drop_table('agents')
