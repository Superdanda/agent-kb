"""Add skill sharing tables

Revision ID: 011_add_skills
Revises: 010_alter_task_created_by_nullable
Create Date: 2026-04-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import CHAR, JSON


revision: str = "011_add_skills"
down_revision: Union[str, None] = "010_alter_task_created_by_nullable"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "skills",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tags_json", JSON, nullable=False),
        sa.Column("current_version_id", CHAR(36), nullable=True),
        sa.Column("uploader_agent_id", CHAR(36), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("uploader_admin_uuid", CHAR(36), nullable=True),
        sa.Column("is_recommended", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_important", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_official", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.Enum("ACTIVE", "HIDDEN", name="skillstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_skills_slug", "skills", ["slug"], unique=True)
    op.create_index("ix_skills_uploader_agent_id", "skills", ["uploader_agent_id"])
    op.create_index("ix_skills_uploader_admin_uuid", "skills", ["uploader_admin_uuid"])

    op.create_table(
        "skill_versions",
        sa.Column("id", CHAR(36), primary_key=True),
        sa.Column("skill_id", CHAR(36), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("summary_snapshot", sa.Text(), nullable=True),
        sa.Column("tags_snapshot", JSON, nullable=False),
        sa.Column("release_note", sa.Text(), nullable=True),
        sa.Column("package_filename", sa.String(512), nullable=False),
        sa.Column("stored_object_key", sa.String(1024), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("metadata_json", JSON, nullable=False),
        sa.Column("created_by_agent_id", CHAR(36), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("created_by_admin_uuid", CHAR(36), nullable=True),
        sa.Column("status", sa.Enum("ACTIVE", "HIDDEN", name="skillversionstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_skill_versions_skill_id", "skill_versions", ["skill_id"])
    op.create_index("ix_skill_versions_sha256", "skill_versions", ["sha256"])
    op.create_index("ix_skill_versions_created_by_agent_id", "skill_versions", ["created_by_agent_id"])
    op.create_index("ix_skill_versions_created_by_admin_uuid", "skill_versions", ["created_by_admin_uuid"])

    op.create_foreign_key(
        "fk_skills_current_version_id",
        "skills",
        "skill_versions",
        ["current_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_skills_current_version_id", "skills", type_="foreignkey")
    op.drop_table("skill_versions")
    op.drop_table("skills")
