"""Replay parse artifact model for Phase 3 parser spike."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Column, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.analysis_job import AnalysisJob
    from app.db.models.upload import Upload
    from app.db.models.user import User


class ReplayParseArtifact(SQLModel, table=True):
    """Normalized replay parser output linked to an analysis job."""

    __tablename__ = "replay_parse_artifacts"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_replay_parse_artifacts_job_id"),
        Index("ix_replay_parse_artifacts_user_created", "user_id", "created_at"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    user_id: uuid.UUID = Field(nullable=False, index=True, foreign_key="users.id")
    upload_id: uuid.UUID = Field(nullable=False, index=True, foreign_key="uploads.id")
    job_id: uuid.UUID | None = Field(default=None, index=True, foreign_key="analysis_jobs.id")
    parser_name: str = Field(default="clarity", max_length=100)
    parser_version: str | None = Field(default=None, max_length=100)
    schema_version: str = Field(default="deadlock-replay-parse-v1", max_length=100)
    status: str = Field(max_length=50)
    artifact: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    warnings: list[str] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False, server_default="[]"))
    error_message: str | None = Field(default=None, max_length=500)
    parse_duration_ms: int | None = Field(default=None)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    user: "User" = Relationship(back_populates="replay_parse_artifacts")
    upload: "Upload" = Relationship(back_populates="replay_parse_artifacts")
    job: Optional["AnalysisJob"] = Relationship(back_populates="replay_parse_artifact")
