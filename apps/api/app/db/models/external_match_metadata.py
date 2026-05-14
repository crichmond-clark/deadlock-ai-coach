"""External match metadata model — raw API response cached by match_id."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Column, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


class ExternalMatchMetadata(SQLModel, table=True):
    """Cached match metadata from Deadlock Game API."""

    __tablename__ = "external_match_metadata"
    __table_args__ = (UniqueConstraint("match_id", name="uq_external_match_metadata_match_id"),)

    id: uuid.UUID = Field(
        default=None,
        sa_column=Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid()),
    )
    match_id: int = Field(sa_column=Column(BigInteger, nullable=False, index=True))
    raw_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    summary: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    fetched_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
