"""AnalysisJob model — placeholder for Phase 2 async processing."""

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
    from app.db.models.upload import Upload
    from app.db.models.user import User


class AnalysisJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisJob(SQLModel, table=True):
    """Minimal placeholder for Phase 2 async processing.

    Phase 1 creates the table so API and worker boundaries have a stable
    target later, but does not implement queue behavior yet.
    Model names, prompt versions, token/cost tracking, and AI output JSON
    belong to Phase 2/3 when the worker and AI workflow design is known.
    """

    __tablename__ = "analysis_jobs"
    __table_args__ = (
        Index("ix_analysis_jobs_user_created", "user_id", "created_at"),
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
    upload_id: uuid.UUID | None = Field(
        default=None,
        index=True,
        foreign_key="uploads.id",
    )
    status: AnalysisJobStatus = Field(
        nullable=False,
        default=AnalysisJobStatus.QUEUED,
        max_length=50,
    )
    progress: int = Field(
        nullable=False,
        default=0,
    )
    error_message: str | None = Field(default=None, max_length=500)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    user: User = Relationship(back_populates="analysis_jobs")
    upload: Upload | None = Relationship(back_populates="analysis_jobs")