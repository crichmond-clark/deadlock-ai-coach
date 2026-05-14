"""Add RAG knowledge source, chunk, and embedding tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_rag_knowledge_tables"
down_revision: str | None = "0007_ai_model_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create pgvector-backed RAG tables."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("patch_version", sa.String(length=50), nullable=True),
        sa.Column("hero_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_sources_content_hash", "knowledge_sources", ["content_hash"])
    op.create_index("ix_knowledge_sources_owner_user_id", "knowledge_sources", ["owner_user_id"])
    op.create_index("ix_knowledge_sources_owner_created", "knowledge_sources", ["owner_user_id", "created_at"])
    op.create_index("ix_knowledge_sources_status", "knowledge_sources", ["status"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("token_count_estimate", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "chunk_index", name="uq_knowledge_chunks_source_index"),
    )
    op.create_index("ix_knowledge_chunks_content_hash", "knowledge_chunks", ["content_hash"])
    op.create_index("ix_knowledge_chunks_source", "knowledge_chunks", ["source_id"])

    op.create_table(
        "knowledge_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["knowledge_chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id", "provider", "model_name", name="uq_knowledge_embeddings_chunk_provider_model"),
    )
    op.create_index("ix_knowledge_embeddings_chunk", "knowledge_embeddings", ["chunk_id"])
    op.create_index("ix_knowledge_embeddings_provider_model", "knowledge_embeddings", ["provider", "model_name"])


def downgrade() -> None:
    """Drop RAG tables."""
    op.drop_index("ix_knowledge_embeddings_provider_model", table_name="knowledge_embeddings")
    op.drop_index("ix_knowledge_embeddings_chunk", table_name="knowledge_embeddings")
    op.drop_table("knowledge_embeddings")
    op.drop_index("ix_knowledge_chunks_source", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_content_hash", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_sources_status", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_owner_created", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_owner_user_id", table_name="knowledge_sources")
    op.drop_index("ix_knowledge_sources_content_hash", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
