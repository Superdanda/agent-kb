"""Add admin user profile fields

Revision ID: 013_add_admin_user_profile_fields
Revises: 012_add_task_leases_and_activity_logs
Create Date: 2026-04-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013_add_admin_user_profile_fields"
down_revision: Union[str, None] = "012_add_task_leases_and_activity_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admin_users", sa.Column("nickname", sa.String(128), nullable=True))
    op.add_column("admin_users", sa.Column("avatar_object_key", sa.String(1024), nullable=True))
    op.add_column("admin_users", sa.Column("avatar_url", sa.String(1024), nullable=True))
    op.add_column("admin_users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("admin_users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("admin_users", sa.Column("phone", sa.String(64), nullable=True))
    op.add_column(
        "admin_users",
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
    )
    op.execute("UPDATE admin_users SET uuid = UUID() WHERE uuid IS NULL")
    op.alter_column("admin_users", "status", server_default=None)


def downgrade() -> None:
    op.drop_column("admin_users", "status")
    op.drop_column("admin_users", "phone")
    op.drop_column("admin_users", "email")
    op.drop_column("admin_users", "bio")
    op.drop_column("admin_users", "avatar_url")
    op.drop_column("admin_users", "avatar_object_key")
    op.drop_column("admin_users", "nickname")
