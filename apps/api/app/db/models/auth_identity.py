"""AuthIdentity model — external OAuth provider identity mapping."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from app.db.models import BaseModel

if TYPE_CHECKING:
    from app.db.models.user import User


class AuthIdentity(BaseModel, table=True):
    """Maps an external OAuth/auth provider identity to one backend User.

    Better Auth/Next.js owns browser auth; the backend only needs stable
    identity mapping via this table. No OAuth tokens are stored here.
    """

    __tablename__ = "auth_identities"

    # Foreign key to users.id
    user_id: uuid.UUID = Field(
        nullable=False,
        index=True,
        foreign_key="users.id",
    )

    # Provider name: discord, github, or dev (local dev provider)
    provider: str = Field(nullable=False, max_length=50)

    # Stable provider user ID / subject claim
    provider_subject: str = Field(nullable=False, max_length=255)

    # Provider email at time of linking, optional
    email: str | None = Field(default=None, max_length=255)

    # Relationship
    user: User = Relationship(back_populates="auth_identities")
