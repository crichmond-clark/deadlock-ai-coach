"""Strategy knowledge search endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import resolve_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.retrieval import StrategySearchRequest, StrategySearchResponse
from app.services.rag.search import StrategySearchError, search_strategy_knowledge

router = APIRouter()

CurrentUser = Annotated[User, Depends(resolve_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/strategy-search", response_model=StrategySearchResponse)
async def strategy_search(
    body: StrategySearchRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> StrategySearchResponse:
    """Search accessible strategy knowledge and return citation-ready chunks."""
    try:
        results = await search_strategy_knowledge(
            db,
            user_id=current_user.id,
            query=body.query,
            top_k=body.top_k,
            hero_ids=body.hero_ids,
            tags=body.tags,
            include_global=body.include_global,
        )
    except StrategySearchError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return StrategySearchResponse(query=body.query, results=results, warnings=[] if results else ["No results found"])
