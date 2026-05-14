"""Tests for embedding providers."""

import pytest

from app.embeddings.errors import EmbeddingProviderInvalidResponseError
from app.embeddings.providers.mock import MockEmbeddingProvider
from app.embeddings.providers.openai_compatible import OpenAICompatibleEmbeddingProvider


@pytest.mark.asyncio
async def test_mock_embedding_provider_is_deterministic():
    provider = MockEmbeddingProvider(dimensions=8)

    first = await provider.embed_texts(["farm souls", "take guardian"], model="mock")
    second = await provider.embed_texts(["farm souls"], model="mock")

    assert first.provider == "mock"
    assert first.dimensions == 8
    assert first.embeddings[0] == second.embeddings[0]
    assert len(first.embeddings[1]) == 8


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider_success(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://example.test/v1/embeddings",
        json={"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}], "usage": {"total_tokens": 3}},
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        timeout_seconds=5,
        dimensions=3,
    )

    response = await provider.embed_texts(["lane pressure"], model="embed-test")

    assert response.embeddings == [[0.1, 0.2, 0.3]]
    assert response.usage["total_tokens"] == 3


@pytest.mark.asyncio
async def test_openai_compatible_embedding_provider_validates_dimensions(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://example.test/v1/embeddings",
        json={"data": [{"index": 0, "embedding": [0.1]}]},
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        timeout_seconds=5,
        dimensions=3,
    )

    with pytest.raises(EmbeddingProviderInvalidResponseError):
        await provider.embed_texts(["lane pressure"], model="embed-test")
