"""Knowledge embedding model using pgvector."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.knowledge_chunk import KnowledgeChunk


class KnowledgeEmbedding(SQLModel, table=True):
    """Vector embedding for one knowledge chunk and embedding model."""

    __tablename__ = "knowledge_embeddings"
    __table_args__ = (
        UniqueConstraint("chunk_id", "provider", "model_name", name="uq_knowledge_embeddings_chunk_provider_model"),
        Index("ix_knowledge_embeddings_chunk", "chunk_id"),
        Index("ix_knowledge_embeddings_provider_model", "provider", "model_name"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    chunk_id: uuid.UUID = Field(nullable=False, foreign_key="knowledge_chunks.id")
    provider: str = Field(max_length=50)
    model_name: str = Field(max_length=100)
    dimensions: int = Field(nullable=False)
    embedding: list[float] = Field(sa_column=Column(Vector(1536), nullable=False))
    embedding_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSONB, nullable=False))
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    chunk: "KnowledgeChunk" = Relationship(back_populates="embeddings")
