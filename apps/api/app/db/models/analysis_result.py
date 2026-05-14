"""AnalysisResult model — persisted fake or structured AI analysis output."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Column, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.ai_model_run import AIModelRun
    from app.db.models.analysis_job import AnalysisJob
    from app.db.models.upload import Upload
    from app.db.models.user import User


class AnalysisResult(SQLModel, table=True):
    """Structured analysis result persisted by the worker."""

    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_analysis_results_job_id"),
        Index("ix_analysis_results_user_created", "user_id", "created_at"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=func.gen_random_uuid(),
        ),
    )
    user_id: uuid.UUID = Field(nullable=False, index=True, foreign_key="users.id")
    job_id: uuid.UUID = Field(nullable=False, foreign_key="analysis_jobs.id")
    upload_id: uuid.UUID | None = Field(default=None, index=True, foreign_key="uploads.id")
    result_kind: str = Field(default="fake_analysis", max_length=50)
    schema_version: str = Field(default="fake-analysis-v1", max_length=50)
    title: str = Field(max_length=255)
    summary: str = Field(max_length=1000)
    payload: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        ),
    )

    user: "User" = Relationship(back_populates="analysis_results")
    job: "AnalysisJob" = Relationship(back_populates="result")
    upload: Optional["Upload"] = Relationship(back_populates="analysis_results")
    ai_model_runs: list["AIModelRun"] = Relationship(back_populates="analysis_result")
