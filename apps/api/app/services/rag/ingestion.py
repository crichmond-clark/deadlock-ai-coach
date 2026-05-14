"""Knowledge source ingestion pipeline."""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.db.models import KnowledgeChunk, KnowledgeEmbedding, KnowledgeSource
from app.embeddings import EmbeddingError, get_embedding_provider
from app.schemas.knowledge import KnowledgeSourceCreateRequest
from app.services.rag.chunking import chunk_text, content_hash


class KnowledgeIngestionError(Exception):
    """Raised when source ingestion cannot complete."""


async def ingest_knowledge_source(
    db: AsyncSession,
    *,
    owner_user_id,
    request: KnowledgeSourceCreateRequest,
) -> KnowledgeSource:
    """Create or update a user-owned knowledge source and embeddings."""
    if len(request.content) > settings.rag_max_source_chars:
        raise KnowledgeIngestionError(f"content exceeds maximum length of {settings.rag_max_source_chars} characters")

    source_hash = content_hash(request.content)
    result = await db.execute(
        select(KnowledgeSource).where(
            KnowledgeSource.owner_user_id == owner_user_id,
            KnowledgeSource.content_hash == source_hash,
        )
    )
    source = result.scalar_one_or_none()

    if source is None:
        source = KnowledgeSource(
            owner_user_id=owner_user_id,
            source_type=request.source_type,
            title=request.title,
            url=request.url,
            content_hash=source_hash,
            raw_content=request.content,
            status="processing",
            patch_version=request.patch_version,
            hero_ids=request.hero_ids,
            tags=request.tags,
            source_metadata=request.metadata,
        )
        db.add(source)
        await db.flush()
    else:
        source.title = request.title
        source.source_type = request.source_type
        source.url = request.url
        source.raw_content = request.content
        source.status = "processing"
        source.patch_version = request.patch_version
        source.hero_ids = request.hero_ids
        source.tags = request.tags
        source.source_metadata = request.metadata
        source.error_message = None
        await db.flush()
        await _delete_source_chunks(db, source.id)

    chunks = chunk_text(
        request.content,
        chunk_size=settings.rag_chunk_size_chars,
        overlap=settings.rag_chunk_overlap_chars,
    )
    if not chunks:
        source.status = "failed"
        source.error_message = "No chunkable content found"
        await db.flush()
        raise KnowledgeIngestionError(source.error_message)

    provider = get_embedding_provider()
    try:
        embeddings = await provider.embed_texts([chunk.content for chunk in chunks], model=settings.embedding_model)
    except EmbeddingError as exc:
        source.status = "failed"
        source.error_message = str(exc)
        await db.flush()
        raise KnowledgeIngestionError(str(exc)) from exc

    if len(embeddings.embeddings) != len(chunks):
        source.status = "failed"
        source.error_message = "Embedding provider returned the wrong number of vectors"
        await db.flush()
        raise KnowledgeIngestionError(source.error_message)

    for chunk, embedding in zip(chunks, embeddings.embeddings, strict=True):
        chunk_row = KnowledgeChunk(
            source_id=source.id,
            chunk_index=chunk.index,
            content=chunk.content,
            content_hash=chunk.content_hash,
            token_count_estimate=chunk.token_count_estimate,
            chunk_metadata={"source_type": request.source_type},
        )
        db.add(chunk_row)
        await db.flush()
        db.add(
            KnowledgeEmbedding(
                chunk_id=chunk_row.id,
                provider=embeddings.provider,
                model_name=embeddings.model,
                dimensions=embeddings.dimensions,
                embedding=embedding,
                embedding_metadata={"usage": embeddings.usage},
            )
        )

    source.status = "ready"
    source.error_message = None
    await db.flush()
    await db.refresh(source)
    return source


async def _delete_source_chunks(db: AsyncSession, source_id) -> None:
    chunk_ids_result = await db.execute(select(KnowledgeChunk.id).where(KnowledgeChunk.source_id == source_id))
    chunk_ids = list(chunk_ids_result.scalars().all())
    if chunk_ids:
        await db.execute(delete(KnowledgeEmbedding).where(KnowledgeEmbedding.chunk_id.in_(chunk_ids)))
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_id == source_id))
