"""Strategy retrieval schemas."""

import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator


class StrategySearchRequest(BaseModel):
    """Request for semantic strategy search."""

    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    hero_ids: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    include_global: bool = True

    @field_validator("query")
    @classmethod
    def strip_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query cannot be empty")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return sorted({tag.strip().lower() for tag in value if tag.strip()})


class StrategySearchResult(BaseModel):
    """Citation-ready strategy search result."""

    chunk_id: uuid.UUID
    source_id: uuid.UUID
    title: str
    snippet: str
    score: float
    citation_label: str
    url: str | None = None
    patch_version: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StrategySearchResponse(BaseModel):
    """Semantic strategy search response."""

    query: str
    results: list[StrategySearchResult]
    warnings: list[str] = Field(default_factory=list)


class RetrievalContext(BaseModel):
    """Compact retrieval context for AI prompts."""

    query: str
    results: list[StrategySearchResult]
    warnings: list[str] = Field(default_factory=list)
