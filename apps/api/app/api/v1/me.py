"""Current user endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class MeResponse(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


@router.get("/me", response_model=MeResponse)
async def get_me() -> MeResponse:
    """Placeholder: returns a mock user for Phase 1.

    Phase 1D will implement real auth with Better Auth token validation.
    """
    return MeResponse(
        id="00000000-0000-0000-0000-000000000001",
        email=None,
        display_name="Local Dev User",
        avatar_url=None,
    )
