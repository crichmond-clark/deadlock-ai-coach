"""Provider protocol and request/response models for chat JSON generation."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """One chat message sent to a model provider."""

    role: Literal["system", "user", "assistant"]
    content: str


class AIRequestOptions(BaseModel):
    """Provider-independent generation options."""

    model: str
    temperature: float = 0.2
    max_output_tokens: int = 2500
    timeout_seconds: float = 45.0


class AIProviderResponse(BaseModel):
    """Normalized response from an AI provider."""

    content: dict[str, Any]
    raw_text: str | None = None
    model_name: str
    provider: str
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    response_metadata: dict[str, Any] = Field(default_factory=dict)


class ChatModelProvider(Protocol):
    """Protocol implemented by all chat model providers."""

    async def generate_json(
        self,
        *,
        messages: list[ChatMessage],
        schema_name: str,
        schema_json: dict[str, Any],
        options: AIRequestOptions,
    ) -> AIProviderResponse:
        """Generate JSON matching the requested schema."""
