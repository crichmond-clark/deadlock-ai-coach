"""Game asset model — items, abilities, upgrades cached from Deadlock Assets API."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


class GameAsset(SQLModel, table=True):
    """Item/ability/upgrade record cached from assets.deadlock-api.com."""

    __tablename__ = "game_assets"

    id: int = Field(sa_column=Column(Integer, primary_key=True, autoincrement=False, nullable=False))
    name: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    class_name: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    asset_kind: str | None = Field(default=None, max_length=50)
    image_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    raw_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    fetched_at: datetime = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
