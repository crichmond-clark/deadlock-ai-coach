"""User model — backend-owned user identity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app.db.models import BaseModel

if TYPE_CHECKING:
    from app.db.models.analysis_job import AnalysisJob
    from app.db.models.auth_identity import AuthIdentity
    from app.db.models.upload import Upload


class User(BaseModel, table=True):
    """Backend-owned user record.

    Stays provider-agnostic. Better Auth/Next.js owns browser auth;
    this table exists so FastAPI can map auth tokens to a stable user ID.
    """

    __tablename__ = "users"

    # Nullable: some OAuth providers may not return an email
    email: str | None = Field(default=None, max_length=255, index=True)

    # Display name from provider or local profile
    display_name: str | None = Field(default=None, max_length=255)

    # Optional provider avatar URL
    avatar_url: str | None = Field(default=None, max_length=500)

    # Relationships
    auth_identities: list[AuthIdentity] = Relationship(
        back_populates="user",
    )
    uploads: list[Upload] = Relationship(
        back_populates="user",
    )
    analysis_jobs: list[AnalysisJob] = Relationship(
        back_populates="user",
    )
