"""OpenAI embedding provider."""

from app.embeddings.providers.openai_compatible import OpenAICompatibleEmbeddingProvider


class OpenAIEmbeddingProvider(OpenAICompatibleEmbeddingProvider):
    """Embedding adapter for OpenAI's embeddings API."""

    provider_name = "openai"

    def __init__(self, *, api_key: str, timeout_seconds: float, dimensions: int) -> None:
        super().__init__(
            base_url="https://api.openai.com/v1",
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            dimensions=dimensions,
        )
