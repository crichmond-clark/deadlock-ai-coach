"""Normalized embedding provider errors."""


class EmbeddingError(Exception):
    """Base error for embedding and retrieval failures."""


class EmbeddingProviderConfigurationError(EmbeddingError):
    """Raised when an embedding provider is not configured."""


class EmbeddingProviderError(EmbeddingError):
    """Raised when an embedding provider call fails."""


class EmbeddingProviderTimeoutError(EmbeddingProviderError):
    """Raised when an embedding provider times out."""


class EmbeddingProviderInvalidResponseError(EmbeddingProviderError):
    """Raised when an embedding provider returns malformed data."""
