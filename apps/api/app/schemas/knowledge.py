"""Knowledge source API schemas."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

KnowledgeSourceType = Literal["text", "markdown", "note", "patch_notes", "guide"]


class KnowledgeSourceCreateRequest(BaseModel):
    """Request to ingest a pasted strategy source."""

    title: str = Field(..., min_length=1, max_length=255)
    source_type: KnowledgeSourceType = "text"
    content: str = Field(..., min_length=1)
    url: str | None = Field(default=None, max_length=1000)
    patch_version: str | None = Field(default=None, max_length=50)
    hero_ids: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "content")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        tags = sorted({tag.strip().lower() for tag in value if tag.strip()})
        if any(len(tag) > 50 for tag in tags):
            raise ValueError("tags must be 50 characters or fewer")
        return tags


class KnowledgeSourceResponse(BaseModel):
    """Knowledge source response."""

    id: uuid.UUID
    owner_user_id: uuid.UUID | None
    source_type: str
    title: str
    url: str | None
    status: str
    patch_version: str | None
    hero_ids: list[int]
    tags: list[str]
    chunk_count: int = 0
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class KnowledgeSourceListResponse(BaseModel):
    """List of accessible knowledge sources."""

    sources: list[KnowledgeSourceResponse]
    total: int
