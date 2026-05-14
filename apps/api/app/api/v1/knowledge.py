"""Knowledge source ingestion and listing endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.auth.dependencies import resolve_current_user
from app.db.models import KnowledgeChunk, KnowledgeSource, User
from app.db.session import get_db
from app.schemas.knowledge import (
    KnowledgeSourceCreateRequest,
    KnowledgeSourceListResponse,
    KnowledgeSourceResponse,
)
from app.services.rag.ingestion import KnowledgeIngestionError, ingest_knowledge_source

router = APIRouter()

CurrentUser = Annotated[User, Depends(resolve_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/knowledge-sources", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def create_knowledge_source(
    body: KnowledgeSourceCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> KnowledgeSourceResponse:
    """Ingest a pasted private strategy knowledge source."""
    try:
        source = await ingest_knowledge_source(db, owner_user_id=current_user.id, request=body)
    except KnowledgeIngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return await _source_response(db, source)


@router.get("/knowledge-sources", response_model=KnowledgeSourceListResponse)
async def list_knowledge_sources(
    current_user: CurrentUser,
    db: DBSession,
) -> KnowledgeSourceListResponse:
    """List user-owned and global knowledge sources."""
    result = await db.execute(
        select(KnowledgeSource)
        .where((KnowledgeSource.owner_user_id == current_user.id) | (KnowledgeSource.owner_user_id.is_(None)))
        .order_by(KnowledgeSource.created_at.desc())
        .limit(100)
    )
    sources = list(result.scalars().all())
    return KnowledgeSourceListResponse(
        sources=[await _source_response(db, source) for source in sources],
        total=len(sources),
    )


async def _source_response(db: AsyncSession, source: KnowledgeSource) -> KnowledgeSourceResponse:
    count_result = await db.execute(
        select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id)
    )
    chunk_count = count_result.scalar() or 0
    return KnowledgeSourceResponse(
        id=source.id,
        owner_user_id=source.owner_user_id,
        source_type=source.source_type,
        title=source.title,
        url=source.url,
        status=source.status,
        patch_version=source.patch_version,
        hero_ids=source.hero_ids or [],
        tags=source.tags or [],
        chunk_count=chunk_count,
        error_message=source.error_message,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )
