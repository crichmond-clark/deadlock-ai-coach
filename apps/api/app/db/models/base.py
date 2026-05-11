"""SQLModel base and shared conventions."""

import uuid
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlmodel import Field, SQLModel


class TimestampMixin:
    """Adds created_at and updated_at timestamp columns."""

    created_at: datetime = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={
            "server_default": func.now(),
            "timezone": True,
        },
    )
    updated_at: datetime = Field(
        default=None,
        nullable=False,
        sa_column_kwargs={
            "server_default": func.now(),
            "onupdate": func.now(),
            "timezone": True,
        },
    )


class UUIDMixin:
    """Adds a server-generated UUID primary key."""

    id: uuid.UUID = Field(
        default=None,
        nullable=False,
        primary_key=True,
        sa_column=Column(
            UUID(as_uuid=True),
            primary_key=True,
            server_default=func.gen_random_uuid(),
        ),
    )


class BaseModel(SQLModel, TimestampMixin, UUIDMixin):
    """Base model class combining UUID and timestamp mixins."""

    pass
