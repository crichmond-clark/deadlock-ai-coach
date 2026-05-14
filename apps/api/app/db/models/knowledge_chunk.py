"""Knowledge chunk model for RAG strategy retrieval."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.knowledge_embedding import KnowledgeEmbedding
    from app.db.models.knowledge_source import KnowledgeSource


class KnowledgeChunk(SQLModel, table=True):
    """Chunked source content with stable hashes and metadata."""

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("source_id", "chunk_index", name="uq_knowledge_chunks_source_index"),
        Index("ix_knowledge_chunks_source", "source_id"),
        Index("ix_knowledge_chunks_content_hash", "content_hash"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    source_id: uuid.UUID = Field(nullable=False, foreign_key="knowledge_sources.id")
    chunk_index: int = Field(nullable=False)
    content: str = Field(sa_column=Column(Text, nullable=False))
    content_hash: str = Field(max_length=64)
    token_count_estimate: int | None = Field(default=None)
    chunk_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSONB, nullable=False))
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    source: "KnowledgeSource" = Relationship(back_populates="chunks")
    embeddings: list["KnowledgeEmbedding"] = Relationship(back_populates="chunk")
