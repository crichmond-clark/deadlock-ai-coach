"""User model — backend-owned user identity."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.analysis_job import AnalysisJob
    from app.db.models.analysis_result import AnalysisResult
    from app.db.models.auth_identity import AuthIdentity
    from app.db.models.replay_parse_artifact import ReplayParseArtifact
    from app.db.models.upload import Upload


class User(SQLModel, table=True):
    """Backend-owned user record.

    Stays provider-agnostic. Better Auth/Next.js owns browser auth;
    this table exists so FastAPI can map auth tokens to a stable user ID.
    """

    __tablename__ = "users"

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    email: str | None = Field(default=None, max_length=255, index=True)
    display_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    auth_identities: list["AuthIdentity"] = Relationship(back_populates="user")
    uploads: list["Upload"] = Relationship(back_populates="user")
    analysis_jobs: list["AnalysisJob"] = Relationship(back_populates="user")
    analysis_results: list["AnalysisResult"] = Relationship(back_populates="user")
    replay_parse_artifacts: list["ReplayParseArtifact"] = Relationship(back_populates="user")
