"""AI model run audit records for structured analysis calls."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Column, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.analysis_job import AnalysisJob
    from app.db.models.analysis_result import AnalysisResult
    from app.db.models.user import User


class AIModelRunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    """Return enum values for SQLAlchemy PostgreSQL enum persistence."""
    return [member.value for member in enum_cls]


class AIModelRun(SQLModel, table=True):
    """Auditable metadata for one AI model call."""

    __tablename__ = "ai_model_runs"
    __table_args__ = (
        Index("ix_ai_model_runs_user_created", "user_id", "created_at"),
        Index("ix_ai_model_runs_job_created", "job_id", "created_at"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    user_id: uuid.UUID = Field(nullable=False, index=True, foreign_key="users.id")
    job_id: uuid.UUID = Field(nullable=False, index=True, foreign_key="analysis_jobs.id")
    analysis_result_id: uuid.UUID | None = Field(default=None, foreign_key="analysis_results.id")
    provider: str = Field(max_length=80)
    model_name: str = Field(max_length=160)
    prompt_version: str = Field(max_length=80)
    workflow_version: str = Field(max_length=80)
    schema_version: str = Field(max_length=80)
    status: AIModelRunStatus = Field(
        sa_column=Column(
            Enum(AIModelRunStatus, name="aimodelrunstatus", values_callable=enum_values),
            nullable=False,
        )
    )
    latency_ms: int | None = Field(default=None)
    input_tokens: int | None = Field(default=None)
    output_tokens: int | None = Field(default=None)
    total_tokens: int | None = Field(default=None)
    request_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    response_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    error_message: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    user: "User" = Relationship(back_populates="ai_model_runs")
    job: "AnalysisJob" = Relationship(back_populates="ai_model_runs")
    analysis_result: Optional["AnalysisResult"] = Relationship(back_populates="ai_model_runs")
