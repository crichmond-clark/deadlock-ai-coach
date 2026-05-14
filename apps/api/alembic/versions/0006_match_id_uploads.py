"""add match_id upload kind and field

Revision ID: 0006_match_id_uploads
Revises: 0005_external_match_metadata
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_match_id_uploads"
down_revision: str | None = "0005_external_match_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPLOAD_KINDS = ("replay", "screenshot", "match_summary", "match_id")


def upgrade() -> None:
    op.execute("ALTER TYPE uploadkind RENAME TO uploadkind_old")
    op.execute(f"CREATE TYPE uploadkind AS ENUM {UPLOAD_KINDS}")
    op.execute(
        "ALTER TABLE uploads ALTER COLUMN kind TYPE uploadkind USING kind::text::uploadkind"
    )
    op.execute("DROP TYPE uploadkind_old")
    op.add_column("uploads", sa.Column("match_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("uploads", "match_id")
    op.execute("DELETE FROM uploads WHERE kind = 'match_id'")
    op.execute("ALTER TYPE uploadkind RENAME TO uploadkind_old2")
    op.execute("CREATE TYPE uploadkind AS ENUM ('replay', 'screenshot', 'match_summary')")
    op.execute(
        "ALTER TABLE uploads ALTER COLUMN kind TYPE uploadkind USING kind::text::uploadkind"
    )
    op.execute("DROP TYPE uploadkind_old2")
