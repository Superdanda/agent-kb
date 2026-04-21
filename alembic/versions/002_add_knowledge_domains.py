"""Add knowledge_domains table

Revision ID: 002_add_knowledge_domains
Revises: 001_init
Create Date: 2026-04-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR

# revision identifiers, used by Alembic.
revision: str = '002_add_knowledge_domains'
down_revision: Union[str, None] = '001_init'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create knowledge_domains table
    op.create_table(
        'knowledge_domains',
        sa.Column('id', CHAR(36), primary_key=True),
        sa.Column('code', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('icon', sa.String(64), nullable=True),
        sa.Column('color', sa.String(16), nullable=True),
        sa.Column('sort_order', sa.Integer, default=0, nullable=False),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    op.create_index('ix_knowledge_domains_code', 'knowledge_domains', ['code'], unique=True)

    # Add domain_id FK to posts table (nullable first, then we'll backfill)
    op.add_column('posts', sa.Column('domain_id', CHAR(36), sa.ForeignKey('knowledge_domains.id'), nullable=True))
    op.create_index('ix_posts_domain_id', 'posts', ['domain_id'])

    # Insert default domains
    op.execute("""
        INSERT INTO knowledge_domains (id, code, name, description, icon, color, sort_order, is_active, created_at, updated_at) VALUES
        (UUID(), 'office', 'Office办公', 'Word、Excel、PPT等办公软件操作指南', '📊', '#4CAF50', 1, TRUE, NOW(), NOW()),
        (UUID(), 'law', '法律领域', '法律法规解读、法律咨询、合同模板等', '⚖️', '#2196F3', 2, TRUE, NOW(), NOW()),
        (UUID(), 'coding', '编程领域', '软件开发、代码实现、技术文档等', '💻', '#9C27B0', 3, TRUE, NOW(), NOW()),
        (UUID(), 'ops', '运维领域', '服务器运维、DevOps、云原生等', '🖥️', '#FF9800', 4, TRUE, NOW(), NOW()),
        (UUID(), 'finance', '财务金融', '财务报表分析、投资理财、审计税务等', '💰', '#607D8B', 5, TRUE, NOW(), NOW()),
        (UUID(), 'hr', '人力资源', '招聘培训、绩效管理、员工关系等', '👥', '#E91E63', 6, TRUE, NOW(), NOW()),
        (UUID(), 'marketing', '市场营销', '品牌推广、活动策划、数字营销等', '📢', '#00BCD4', 7, TRUE, NOW(), NOW()),
        (UUID(), 'design', '设计创意', 'UI设计、视觉设计、创意方案等', '🎨', '#8BC34A', 8, TRUE, NOW(), NOW())
    """)


def downgrade() -> None:
    op.drop_index('ix_posts_domain_id', 'posts')
    op.drop_column('posts', 'domain_id')
    op.drop_table('knowledge_domains')
