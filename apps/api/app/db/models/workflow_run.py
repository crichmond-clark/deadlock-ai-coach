"""Workflow run telemetry model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.analysis_job import AnalysisJob
    from app.db.models.user import User
    from app.db.models.workflow_step import WorkflowStep


class WorkflowRun(SQLModel, table=True):
    """One analysis workflow execution attempt."""

    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index("ix_workflow_runs_job_created", "job_id", "created_at"),
        Index("ix_workflow_runs_user_created", "user_id", "created_at"),
        Index("ix_workflow_runs_status", "status"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    user_id: uuid.UUID = Field(nullable=False, index=True, foreign_key="users.id")
    job_id: uuid.UUID = Field(nullable=False, index=True, foreign_key="analysis_jobs.id")
    workflow_name: str = Field(default="analysis", max_length=80)
    workflow_version: str = Field(max_length=80)
    engine: str = Field(default="simple", max_length=50)
    status: str = Field(default="running", max_length=30)
    started_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    duration_ms: int | None = Field(default=None)
    state_snapshot: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    user: "User" = Relationship(back_populates="workflow_runs")
    job: "AnalysisJob" = Relationship(back_populates="workflow_runs")
    steps: list["WorkflowStep"] = Relationship(back_populates="workflow_run")
