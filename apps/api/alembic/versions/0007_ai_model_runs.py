"""add ai model run audit table

Revision ID: 0007_ai_model_runs
Revises: 0006_match_id_uploads
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_ai_model_runs"
down_revision: str | None = "0006_match_id_uploads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_model_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_result_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False),
        sa.Column("prompt_version", sa.String(length=80), nullable=False),
        sa.Column("workflow_version", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.Enum("succeeded", "failed", name="aimodelrunstatus"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("request_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_result_id"], ["analysis_results.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_model_runs_job_id"), "ai_model_runs", ["job_id"], unique=False)
    op.create_index("ix_ai_model_runs_job_created", "ai_model_runs", ["job_id", "created_at"], unique=False)
    op.create_index(op.f("ix_ai_model_runs_user_id"), "ai_model_runs", ["user_id"], unique=False)
    op.create_index("ix_ai_model_runs_user_created", "ai_model_runs", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ai_model_runs_user_created", table_name="ai_model_runs")
    op.drop_index(op.f("ix_ai_model_runs_user_id"), table_name="ai_model_runs")
    op.drop_index("ix_ai_model_runs_job_created", table_name="ai_model_runs")
    op.drop_index(op.f("ix_ai_model_runs_job_id"), table_name="ai_model_runs")
    op.drop_table("ai_model_runs")
    op.execute("DROP TYPE IF EXISTS aimodelrunstatus")
