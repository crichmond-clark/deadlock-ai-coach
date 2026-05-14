"""Knowledge source model for RAG strategy notes."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Column, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.knowledge_chunk import KnowledgeChunk
    from app.db.models.user import User


class KnowledgeSource(SQLModel, table=True):
    """User-owned or global knowledge source for strategy retrieval."""

    __tablename__ = "knowledge_sources"
    __table_args__ = (
        Index("ix_knowledge_sources_owner_created", "owner_user_id", "created_at"),
        Index("ix_knowledge_sources_status", "status"),
        Index("ix_knowledge_sources_content_hash", "content_hash"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    owner_user_id: uuid.UUID | None = Field(default=None, index=True, foreign_key="users.id")
    source_type: str = Field(default="text", max_length=50)
    title: str = Field(max_length=255)
    url: str | None = Field(default=None, max_length=1000)
    content_hash: str = Field(max_length=64)
    raw_content: str = Field(sa_column=Column(Text, nullable=False))
    status: str = Field(default="processing", max_length=30)
    patch_version: str | None = Field(default=None, max_length=50)
    hero_ids: list[int] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    source_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSONB, nullable=False))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    owner: Optional["User"] = Relationship(back_populates="knowledge_sources")
    chunks: list["KnowledgeChunk"] = Relationship(back_populates="source")
