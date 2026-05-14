"""Embedding provider protocol and response models."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class EmbeddingProviderResponse:
    """Normalized response from an embedding provider."""

    embeddings: list[list[float]]
    provider: str
    model: str
    dimensions: int
    usage: dict[str, Any] = field(default_factory=dict)


class EmbeddingProvider(Protocol):
    """Protocol implemented by embedding providers."""

    async def embed_texts(self, texts: list[str], *, model: str) -> EmbeddingProviderResponse:
        """Return one embedding per input text."""
        ...
