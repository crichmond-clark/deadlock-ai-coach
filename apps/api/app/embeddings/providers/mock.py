"""Deterministic embedding provider for local development and tests."""

import hashlib
import math

from app.embeddings.providers.base import EmbeddingProviderResponse


class MockEmbeddingProvider:
    """Generate stable pseudo-embeddings without external API calls."""

    provider_name = "mock"

    def __init__(self, *, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str], *, model: str) -> EmbeddingProviderResponse:
        embeddings = [_embed_text(text, self.dimensions) for text in texts]
        return EmbeddingProviderResponse(
            embeddings=embeddings,
            provider=self.provider_name,
            model=model,
            dimensions=self.dimensions,
            usage={"input_count": len(texts)},
        )


def _embed_text(text: str, dimensions: int) -> list[float]:
    vector = [0.0] * dimensions
    normalized = " ".join(text.lower().split())
    for token in normalized.split() or [normalized]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [round(value / magnitude, 8) for value in vector]
