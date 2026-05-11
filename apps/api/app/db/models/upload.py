"""Upload model — user-submitted input metadata."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Index
from sqlmodel import Field, Relationship

from app.db.models import BaseModel

if TYPE_CHECKING:
    from app.db.models.analysis_job import AnalysisJob
    from app.db.models.user import User


class UploadKind(StrEnum):
    """Kind of user-submitted input artifact."""

    REPLAY = "replay"
    SCREENSHOT = "screenshot"
    MATCH_SUMMARY = "match_summary"


class UploadStatus(StrEnum):
    """Status of the upload metadata record."""

    CREATED = "created"
    UPLOADED = "uploaded"
    FAILED = "failed"


class Upload(BaseModel, table=True):
    """User-submitted input artifact metadata.

    In Phase 1 stores metadata only. Real R2 presigned upload flow comes later.
    Parsed replay fields, hero names, etc. belong to later phases.
    """

    __tablename__ = "uploads"

    # Foreign key to users.id
    user_id: uuid.UUID = Field(
        nullable=False,
        index=True,
        foreign_key="users.id",
    )

    # Kind of artifact: replay, screenshot, or match_summary
    kind: UploadKind = Field(nullable=False, max_length=50)

    # Display filename only — never use as a filesystem path
    filename: str | None = Field(default=None, max_length=255)

    # Client-declared MIME type, informational only
    content_type: str | None = Field(default=None, max_length=100)

    # Declared size; validate against configured limit
    size_bytes: int | None = Field(default=None)

    # Object storage key or local placeholder; server-generated in production
    storage_key: str | None = Field(default=None, max_length=500)

    # Required only when kind = match_summary
    summary_text: str | None = Field(default=None, max_length=10000)

    # Upload metadata status
    status: UploadStatus = Field(
        nullable=False,
        default=UploadStatus.CREATED,
        max_length=50,
    )

    # Relationships
    user: User = Relationship(back_populates="uploads")
    analysis_jobs: list[AnalysisJob] = Relationship(
        back_populates="upload",
    )

    __table_args__ = (
        Index("ix_uploads_user_created", "user_id", "created_at"),
    )
