"""Add task board new statuses

Revision ID: 007
Revises: 006
Create Date: 2026-04-21

Note: TaskStatus enum新增 UNCLAIMED, SUBMITTED, CONFIRMED 三个状态。
这些是枚举值变更，不需要数据库结构迁移。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """新增枚举值不需要结构迁移，仅记录此次变更"""
    pass


def downgrade() -> None:
    pass