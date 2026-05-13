"""Initial foundation models — users, auth identities, uploads, analysis jobs.

Revision ID: 0001
Revises:
Create Date: 2026-05-11

"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, UUID

from alembic import op

# Revision identifiers, used by Alembic.
revision = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ========================================================================
    # Enum types
    # ========================================================================
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE uploadkind AS ENUM ('replay', 'screenshot', 'match_summary');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE uploadstatus AS ENUM ('created', 'uploaded', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE analysisjobstatus AS ENUM ('queued', 'running', 'succeeded', 'failed', 'cancelled');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
        """
    )

    # ========================================================================
    # users
    # ========================================================================
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False, if_not_exists=True)

    # ========================================================================
    # auth_identities
    # ========================================================================
    op.create_table(
        "auth_identities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"], unique=False, if_not_exists=True)
    op.create_index(
        "ix_auth_identities_provider_subject",
        "auth_identities",
        ["provider", "provider_subject"],
        unique=True,
        if_not_exists=True,
    )
    op.create_foreign_key(
        "fk_auth_identities_user_id",
        "auth_identities", "users",
        ["user_id"], ["id"],
    )

    # ========================================================================
    # uploads
    # ========================================================================
    op.create_table(
        "uploads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("kind", ENUM("replay", "screenshot", "match_summary", name="uploadkind", create_type=False), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("summary_text", sa.String(length=10000), nullable=True),
        sa.Column(
            "status",
            ENUM("created", "uploaded", "failed", name="uploadstatus", create_type=False),
            nullable=False,
            server_default="created",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_uploads_user_id", "uploads", ["user_id"], unique=False, if_not_exists=True)
    op.create_index("ix_uploads_user_created", "uploads", ["user_id", "created_at"], unique=False, if_not_exists=True)
    op.create_foreign_key(
        "fk_uploads_user_id",
        "uploads", "users",
        ["user_id"], ["id"],
    )

    # ========================================================================
    # analysis_jobs
    # ========================================================================
    op.create_table(
        "analysis_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("upload_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            ENUM("queued", "running", "succeeded", "failed", "cancelled", name="analysisjobstatus", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_analysis_jobs_user_id", "analysis_jobs", ["user_id"], unique=False, if_not_exists=True)
    op.create_index("ix_analysis_jobs_upload_id", "analysis_jobs", ["upload_id"], unique=False, if_not_exists=True)
    op.create_index("ix_analysis_jobs_user_created", "analysis_jobs", ["user_id", "created_at"], unique=False, if_not_exists=True)
    op.create_foreign_key(
        "fk_analysis_jobs_user_id",
        "analysis_jobs", "users",
        ["user_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_analysis_jobs_upload_id",
        "analysis_jobs", "uploads",
        ["upload_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_table("analysis_jobs")
    op.drop_table("uploads")
    op.drop_table("auth_identities")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS analysisjobstatus")
    op.execute("DROP TYPE IF EXISTS uploadstatus")
    op.execute("DROP TYPE IF EXISTS uploadkind")
