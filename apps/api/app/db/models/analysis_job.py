"""AnalysisJob model — placeholder for Phase 2 async processing."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Index
from sqlmodel import Field, Relationship

from app.db.models import BaseModel

if TYPE_CHECKING:
    from app.db.models.upload import Upload
    from app.db.models.user import User


class AnalysisJobStatus(StrEnum):
    """Status of an analysis job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisJob(BaseModel, table=True):
    """Minimal placeholder for Phase 2 async processing.

    Phase 1 creates the table so API and worker boundaries have a stable
    target later, but does not implement queue behavior yet.
    Model names, prompt versions, token/cost tracking, and AI output JSON
    belong to Phase 2/3 when the worker and AI workflow design is known.
    """

    __tablename__ = "analysis_jobs"

    # Foreign key to users.id
    user_id: uuid.UUID = Field(
        nullable=False,
        index=True,
        foreign_key="users.id",
    )

    # Foreign key to uploads.id, nullable for future non-upload jobs
    upload_id: uuid.UUID | None = Field(
        default=None,
        index=True,
        foreign_key="uploads.id",
    )

    # Job status
    status: AnalysisJobStatus = Field(
        nullable=False,
        default=AnalysisJobStatus.QUEUED,
        max_length=50,
    )

    # Progress percentage 0-100
    progress: int = Field(
        nullable=False,
        default=0,
    )

    # Short safe error message for display/debugging
    error_message: str | None = Field(default=None, max_length=500)

    # Set when worker starts in Phase 2
    started_at: datetime | None = Field(default=None)

    # Set when worker finishes in Phase 2
    completed_at: datetime | None = Field(default=None)

    # Relationships
    user: User = Relationship(back_populates="analysis_jobs")
    upload: Upload | None = Relationship(back_populates="analysis_jobs")

    __table_args__ = (
        Index("ix_analysis_jobs_user_created", "user_id", "created_at"),
    )
