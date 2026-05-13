"""AuthIdentity model — external OAuth provider identity mapping."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.user import User


class AuthIdentity(SQLModel, table=True):
    """Maps an external OAuth/auth provider identity to one backend User.

    Better Auth/Next.js owns browser auth; the backend only needs stable
    identity mapping via this table. No OAuth tokens are stored here.
    """

    __tablename__ = "auth_identities"
    __table_args__ = (
        Index("ix_auth_identities_provider_subject", "provider", "provider_subject", unique=True),
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
    provider: str = Field(nullable=False, max_length=50)
    provider_subject: str = Field(nullable=False, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    updated_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )

    user: "User" = Relationship(back_populates="auth_identities")
