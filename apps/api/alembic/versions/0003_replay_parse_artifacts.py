"""add replay parse artifacts

Revision ID: 0003_replay_parse_artifacts
Revises: 0002_async_pipeline_results
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_replay_parse_artifacts"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "replay_parse_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parser_name", sa.String(length=100), nullable=False),
        sa.Column("parser_version", sa.String(length=100), nullable=True),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("artifact", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("parse_duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["upload_id"], ["uploads.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", name="uq_replay_parse_artifacts_job_id"),
    )
    op.create_index(op.f("ix_replay_parse_artifacts_user_id"), "replay_parse_artifacts", ["user_id"], unique=False)
    op.create_index(op.f("ix_replay_parse_artifacts_upload_id"), "replay_parse_artifacts", ["upload_id"], unique=False)
    op.create_index(op.f("ix_replay_parse_artifacts_job_id"), "replay_parse_artifacts", ["job_id"], unique=False)
    op.create_index("ix_replay_parse_artifacts_user_created", "replay_parse_artifacts", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_replay_parse_artifacts_user_created", table_name="replay_parse_artifacts")
    op.drop_index(op.f("ix_replay_parse_artifacts_job_id"), table_name="replay_parse_artifacts")
    op.drop_index(op.f("ix_replay_parse_artifacts_upload_id"), table_name="replay_parse_artifacts")
    op.drop_index(op.f("ix_replay_parse_artifacts_user_id"), table_name="replay_parse_artifacts")
    op.drop_table("replay_parse_artifacts")
