"""Upload model — user-submitted input metadata."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.analysis_job import AnalysisJob
    from app.db.models.user import User


class UploadKind(StrEnum):
    REPLAY = "replay"
    SCREENSHOT = "screenshot"
    MATCH_SUMMARY = "match_summary"


class UploadStatus(StrEnum):
    CREATED = "created"
    UPLOADED = "uploaded"
    FAILED = "failed"


class Upload(SQLModel, table=True):
    """User-submitted input artifact metadata.

    In Phase 1 stores metadata only. Real R2 presigned upload flow comes later.
    Parsed replay fields, hero names, etc. belong to later phases.
    """

    __tablename__ = "uploads"
    __table_args__ = (
        Index("ix_uploads_user_created", "user_id", "created_at"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    user_id: uuid.UUID = Field(
        nullable=False,
        index=True,
        foreign_key="users.id",
    )
    kind: UploadKind = Field(nullable=False, max_length=50)
    filename: str | None = Field(default=None, max_length=255)
    content_type: str | None = Field(default=None, max_length=100)
    size_bytes: int | None = Field(default=None)
    storage_key: str | None = Field(default=None, max_length=500)
    summary_text: str | None = Field(default=None, max_length=10000)
    status: UploadStatus = Field(
        nullable=False,
        default=UploadStatus.CREATED,
        max_length=50,
    )
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    user: User = Relationship(back_populates="uploads")
    analysis_jobs: list[AnalysisJob] = Relationship(back_populates="upload")