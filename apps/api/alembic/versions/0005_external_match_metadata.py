"""add external_match_metadata table

Revision ID: 0005_external_match_metadata
Revises: 0004_heroes_game_assets
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_external_match_metadata"
down_revision: str | None = "0004_heroes_game_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_match_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", name="uq_external_match_metadata_match_id"),
    )
    op.create_index(op.f("ix_external_match_metadata_match_id"), "external_match_metadata", ["match_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_external_match_metadata_match_id"), table_name="external_match_metadata")
    op.drop_table("external_match_metadata")
