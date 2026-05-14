"""OpenAI-compatible embedding provider."""

from typing import Any

import httpx

from app.embeddings.errors import (
    EmbeddingProviderConfigurationError,
    EmbeddingProviderError,
    EmbeddingProviderInvalidResponseError,
    EmbeddingProviderTimeoutError,
)
from app.embeddings.providers.base import EmbeddingProviderResponse


class OpenAICompatibleEmbeddingProvider:
    """Embedding adapter for OpenAI-compatible `/embeddings` APIs."""

    provider_name = "openai_compatible"

    def __init__(self, *, base_url: str, api_key: str, timeout_seconds: float, dimensions: int) -> None:
        if not base_url:
            raise EmbeddingProviderConfigurationError("EMBEDDING_BASE_URL is required")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str], *, model: str) -> EmbeddingProviderResponse:
        if not texts:
            return EmbeddingProviderResponse([], self.provider_name, model, self.dimensions)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict[str, Any] = {"model": model, "input": texts}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/embeddings", headers=headers, json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise EmbeddingProviderTimeoutError("Embedding provider timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise EmbeddingProviderError(f"Embedding provider returned HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError("Embedding provider request failed") from exc

        return self._parse_response(response.json(), model=model)

    def _parse_response(self, data: dict[str, Any], *, model: str) -> EmbeddingProviderResponse:
        rows = data.get("data")
        if not isinstance(rows, list):
            raise EmbeddingProviderInvalidResponseError("Embedding response missing data list")

        embeddings: list[list[float]] = []
        for row in sorted(rows, key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0):
            if not isinstance(row, dict) or not isinstance(row.get("embedding"), list):
                raise EmbeddingProviderInvalidResponseError("Embedding response row missing embedding list")
            embedding = [float(value) for value in row["embedding"]]
            if len(embedding) != self.dimensions:
                raise EmbeddingProviderInvalidResponseError(
                    f"Embedding dimensions {len(embedding)} did not match configured {self.dimensions}"
                )
            embeddings.append(embedding)

        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        return EmbeddingProviderResponse(
            embeddings=embeddings,
            provider=self.provider_name,
            model=model,
            dimensions=self.dimensions,
            usage=usage,
        )
