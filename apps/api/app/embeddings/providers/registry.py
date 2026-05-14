"""Embedding provider registry."""

from app.core.config import Settings, settings
from app.embeddings.errors import EmbeddingProviderConfigurationError
from app.embeddings.providers.base import EmbeddingProvider
from app.embeddings.providers.mock import MockEmbeddingProvider
from app.embeddings.providers.openai import OpenAIEmbeddingProvider
from app.embeddings.providers.openai_compatible import OpenAICompatibleEmbeddingProvider


def get_embedding_provider(config: Settings = settings) -> EmbeddingProvider:
    """Build the configured embedding provider."""
    if config.embedding_provider == "mock":
        return MockEmbeddingProvider(dimensions=config.embedding_dimensions)

    if config.embedding_provider == "openai":
        api_key = config.embedding_api_key or config.openai_api_key
        if not api_key:
            raise EmbeddingProviderConfigurationError("EMBEDDING_API_KEY or OPENAI_API_KEY is required")
        return OpenAIEmbeddingProvider(
            api_key=api_key,
            timeout_seconds=config.ai_timeout_seconds,
            dimensions=config.embedding_dimensions,
        )

    if config.embedding_provider == "openai_compatible":
        return OpenAICompatibleEmbeddingProvider(
            base_url=config.embedding_base_url,
            api_key=config.embedding_api_key,
            timeout_seconds=config.ai_timeout_seconds,
            dimensions=config.embedding_dimensions,
        )

    raise EmbeddingProviderConfigurationError(f"Unsupported embedding provider: {config.embedding_provider}")
