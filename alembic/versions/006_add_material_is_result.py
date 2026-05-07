"""add material is_result

Revision ID: 006_add_material_is_result
Revises: 005_add_task_board
Create Date: 2026-04-21 22:43:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006_add_material_is_result'
down_revision = '005_add_task_board'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('task_materials', sa.Column('is_result', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('task_materials', 'is_result')
