"""Retrieval context helpers for AI coaching prompts."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.retrieval import RetrievalContext
from app.services.rag.search import StrategySearchError, search_strategy_knowledge


async def retrieve_strategy_context(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    query: str,
    top_k: int | None = None,
    hero_ids: list[int] | None = None,
    tags: list[str] | None = None,
    include_global: bool = True,
) -> RetrievalContext:
    """Return compact strategy context for AI prompts without failing analysis on RAG errors."""
    try:
        results = await search_strategy_knowledge(
            db,
            user_id=user_id,
            query=query,
            top_k=top_k or settings.rag_top_k,
            hero_ids=hero_ids or [],
            tags=tags or [],
            include_global=include_global,
        )
    except StrategySearchError as exc:
        return RetrievalContext(query=query, results=[], warnings=[str(exc)])

    warnings = [] if results else ["No relevant strategy knowledge found"]
    return RetrievalContext(query=query, results=results, warnings=warnings)
