"""Add async pipeline result persistence.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-13

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("analysis_jobs", sa.Column("queue_job_id", sa.String(length=255), nullable=True))
    op.add_column(
        "analysis_jobs",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column(
        "analysis_jobs",
        "started_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )
    op.alter_column(
        "analysis_jobs",
        "completed_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    op.create_table(
        "analysis_results",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", UUID(as_uuid=True), nullable=True),
        sa.Column("result_kind", sa.String(length=50), nullable=False),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("job_id", name="uq_analysis_results_job_id"),
    )
    op.create_index("ix_analysis_results_user_id", "analysis_results", ["user_id"], unique=False)
    op.create_index("ix_analysis_results_upload_id", "analysis_results", ["upload_id"], unique=False)
    op.create_index(
        "ix_analysis_results_user_created",
        "analysis_results",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_results_user_created", table_name="analysis_results")
    op.drop_index("ix_analysis_results_upload_id", table_name="analysis_results")
    op.drop_index("ix_analysis_results_user_id", table_name="analysis_results")
    op.drop_table("analysis_results")
    op.alter_column(
        "analysis_jobs",
        "completed_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "analysis_jobs",
        "started_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.drop_column("analysis_jobs", "attempt_count")
    op.drop_column("analysis_jobs", "queue_job_id")
