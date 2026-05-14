"""Embedding provider package."""

from app.embeddings.errors import (
    EmbeddingError,
    EmbeddingProviderConfigurationError,
    EmbeddingProviderError,
    EmbeddingProviderInvalidResponseError,
    EmbeddingProviderTimeoutError,
)
from app.embeddings.providers.base import EmbeddingProviderResponse
from app.embeddings.providers.registry import get_embedding_provider

__all__ = [
    "EmbeddingError",
    "EmbeddingProviderConfigurationError",
    "EmbeddingProviderError",
    "EmbeddingProviderInvalidResponseError",
    "EmbeddingProviderResponse",
    "EmbeddingProviderTimeoutError",
    "get_embedding_provider",
]
