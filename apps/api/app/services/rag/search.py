"""Strategy knowledge search service."""

import math
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.models import KnowledgeChunk, KnowledgeEmbedding, KnowledgeSource
from app.embeddings import EmbeddingError, get_embedding_provider
from app.schemas.retrieval import StrategySearchResult


class StrategySearchError(Exception):
    """Raised when strategy search cannot complete."""


async def search_strategy_knowledge(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    query: str,
    top_k: int | None = None,
    hero_ids: Sequence[int] | None = None,
    tags: Sequence[str] | None = None,
    include_global: bool = True,
) -> list[StrategySearchResult]:
    """Embed a query and return ranked accessible chunks."""
    provider = get_embedding_provider()
    try:
        response = await provider.embed_texts([query], model=settings.embedding_model)
    except EmbeddingError as exc:
        raise StrategySearchError(str(exc)) from exc

    if not response.embeddings:
        return []

    query_embedding = response.embeddings[0]
    limit = top_k or settings.rag_top_k
    rows = await _load_candidate_rows(db, user_id=user_id, include_global=include_global)
    filtered = [row for row in rows if _matches_filters(row[1], hero_ids=hero_ids or [], tags=tags or [])]

    ranked = sorted(
        ((_cosine_similarity(query_embedding, _as_float_list(row[2].embedding)), row) for row in filtered),
        key=lambda item: item[0],
        reverse=True,
    )[:limit]

    return [_to_result(row, score=score, rank=index + 1) for index, (score, row) in enumerate(ranked)]


async def _load_candidate_rows(db: AsyncSession, *, user_id: uuid.UUID, include_global: bool):
    conditions = [KnowledgeSource.owner_user_id == user_id]
    if include_global:
        conditions.append(KnowledgeSource.owner_user_id.is_(None))
    result = await db.execute(
        select(KnowledgeChunk, KnowledgeSource, KnowledgeEmbedding)
        .join(KnowledgeSource, KnowledgeChunk.source_id == KnowledgeSource.id)
        .join(KnowledgeEmbedding, KnowledgeEmbedding.chunk_id == KnowledgeChunk.id)
        .where(KnowledgeSource.status == "ready")
        .where(KnowledgeSource.owner_user_id.in_([user_id]) if not include_global else conditions[0] | conditions[1])
    )
    return list(result.all())


def _matches_filters(source: KnowledgeSource, *, hero_ids: Sequence[int], tags: Sequence[str]) -> bool:
    if hero_ids and not set(hero_ids).intersection(set(source.hero_ids or [])):
        return False
    return not (tags and not set(tags).issubset(set(source.tags or [])))


def _to_result(row, *, score: float, rank: int) -> StrategySearchResult:
    chunk, source, _embedding = row
    snippet = chunk.content if len(chunk.content) <= 500 else f"{chunk.content[:497].rstrip()}..."
    return StrategySearchResult(
        chunk_id=chunk.id,
        source_id=source.id,
        title=source.title,
        snippet=snippet,
        score=round(score, 6),
        citation_label=f"S{rank}: {source.title}",
        url=source.url,
        patch_version=source.patch_version,
        tags=source.tags or [],
        metadata={
            "chunk_index": chunk.chunk_index,
            "source_type": source.source_type,
            **(chunk.chunk_metadata or {}),
        },
    )


def _as_float_list(value) -> list[float]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    return [float(item) for item in value]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_mag = math.sqrt(sum(a * a for a in left))
    right_mag = math.sqrt(sum(b * b for b in right))
    if left_mag == 0 or right_mag == 0:
        return 0.0
    return dot / (left_mag * right_mag)
