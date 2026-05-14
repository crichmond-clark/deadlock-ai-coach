"""Tests for RAG search and retrieval context."""

import uuid
from unittest.mock import MagicMock

import pytest

from app.db.models import KnowledgeChunk, KnowledgeEmbedding, KnowledgeSource
from app.embeddings.providers.base import EmbeddingProviderResponse
from app.services.rag.context import retrieve_strategy_context
from app.services.rag.search import StrategySearchError, search_strategy_knowledge


class StaticEmbeddingProvider:
    async def embed_texts(self, texts: list[str], *, model: str) -> EmbeddingProviderResponse:
        del texts
        return EmbeddingProviderResponse(
            embeddings=[[1.0, 0.0, 0.0]],
            provider="mock",
            model=model,
            dimensions=3,
        )


def _row(owner_id: uuid.UUID | None, *, title: str, vector: list[float], tags: list[str] | None = None):
    source_id = uuid.uuid4()
    chunk = KnowledgeChunk(
        id=uuid.uuid4(),
        source_id=source_id,
        chunk_index=0,
        content=f"{title} says control waves before fighting.",
        content_hash="hash",
        chunk_metadata={"source_type": "guide"},
    )
    source = KnowledgeSource(
        id=source_id,
        owner_user_id=owner_id,
        source_type="guide",
        title=title,
        content_hash="source-hash",
        raw_content=chunk.content,
        status="ready",
        hero_ids=[1],
        tags=tags or ["laning"],
        source_metadata={},
    )
    embedding = KnowledgeEmbedding(
        id=uuid.uuid4(),
        chunk_id=chunk.id,
        provider="mock",
        model_name="mock",
        dimensions=3,
        embedding=vector,
        embedding_metadata={},
    )
    return chunk, source, embedding


@pytest.mark.asyncio
async def test_search_strategy_knowledge_ranks_accessible_rows(monkeypatch):
    user_id = uuid.uuid4()
    rows = [
        _row(user_id, title="Best result", vector=[1.0, 0.0, 0.0]),
        _row(uuid.uuid4(), title="Private other user", vector=[1.0, 0.0, 0.0]),
        _row(None, title="Global result", vector=[0.5, 0.5, 0.0]),
    ]

    async def fake_load_candidate_rows(db, *, user_id, include_global):
        del db, user_id, include_global
        return [rows[0], rows[2]]

    monkeypatch.setattr("app.services.rag.search.get_embedding_provider", lambda: StaticEmbeddingProvider())
    monkeypatch.setattr("app.services.rag.search.settings.embedding_model", "mock")
    monkeypatch.setattr("app.services.rag.search._load_candidate_rows", fake_load_candidate_rows)

    results = await search_strategy_knowledge(
        MagicMock(),
        user_id=user_id,
        query="wave control",
        top_k=2,
        hero_ids=[1],
        tags=["laning"],
    )

    assert [result.title for result in results] == ["Best result", "Global result"]
    assert results[0].score > results[1].score
    assert results[0].citation_label.startswith("S1:")


@pytest.mark.asyncio
async def test_retrieve_strategy_context_degrades_on_search_error(monkeypatch):
    async def failing_search(*args, **kwargs):
        del args, kwargs
        raise StrategySearchError("boom")

    monkeypatch.setattr("app.services.rag.context.search_strategy_knowledge", failing_search)

    context = await retrieve_strategy_context(MagicMock(), user_id=uuid.uuid4(), query="anything")

    assert context.results == []
    assert context.warnings == ["boom"]
