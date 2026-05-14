"""Workflow step telemetry model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, Index, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.workflow_run import WorkflowRun


class WorkflowStep(SQLModel, table=True):
    """Telemetry for one workflow node execution."""

    __tablename__ = "workflow_steps"
    __table_args__ = (
        Index("ix_workflow_steps_run_name", "workflow_run_id", "step_name"),
        Index("ix_workflow_steps_status", "status"),
    )

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    workflow_run_id: uuid.UUID = Field(nullable=False, index=True, foreign_key="workflow_runs.id")
    step_name: str = Field(max_length=100)
    status: str = Field(default="pending", max_length=30)
    started_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    completed_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    duration_ms: int | None = Field(default=None)
    input_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    output_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    warnings: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSONB, nullable=False))
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    workflow_run: "WorkflowRun" = Relationship(back_populates="steps")
