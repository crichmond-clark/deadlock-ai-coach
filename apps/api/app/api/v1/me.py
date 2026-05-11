"""Current user endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.dependencies import resolve_current_user
from app.db.models import User

router = APIRouter()


class MeResponse(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(resolve_current_user),
) -> MeResponse:
    """Return the authenticated user's profile.

    Requires Authorization header (Bearer token) in production.
    In local development, accepts X-Dev-User-Id header.
    """
    return MeResponse(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
    )