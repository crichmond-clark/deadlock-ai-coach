"""Auth boundary — FastAPI dependency for resolving the current user.

Architecture:
- Better Auth (Next.js) owns browser auth and session handling
- Next.js passes a signed token or session-derived credential to FastAPI
- FastAPI validates the credential and resolves/creates a backend User record
- FastAPI endpoints receive the resolved User via this dependency

Local development:
- When AUTH_SECRET is "local-dev-secret-change-in-production" and a request
  includes X-Dev-User-Id header, we auto-create or find a dev user
- This allows testing auth-protected endpoints without setting up OAuth
"""

import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db


async def resolve_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    x_dev_user_id: Annotated[str | None, Header(alias="X-Dev-User-Id")] = None,
) -> User:
    """Resolve the current authenticated user from request headers.

    In production: validate a Better Auth signed token from the Authorization header.
    In local development: accept X-Dev-User-Id header to bypass real auth.

    Returns the resolved User record.
    Raises 401 if authentication fails.
    """
    from app.core.config import settings

    # ========================================================================
    # Local development: dev token bypass
    # ========================================================================
    if settings.is_local and x_dev_user_id:
        # Dev mode: X-Dev-User-Id header directly provides user identity
        user = await _get_or_create_dev_user(db, x_dev_user_id)
        if user:
            return user

    # ========================================================================
    # Production: validate Better Auth signed token
    # ========================================================================
    # TODO (Phase 1F): Implement Better Auth token validation here.
    # Expected flow:
    # 1. Extract Authorization header (Bearer <token>)
    # 2. Validate JWT using auth_secret
    # 3. Extract provider + subject from token claims
    # 4. Look up or create AuthIdentity + User
    #
    # For now, raise 401 so we don't accidentally leave endpoints open.
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Set Authorization header or use X-Dev-User-Id in local dev.",
    )


async def _get_or_create_dev_user(db: AsyncSession, dev_user_id: str) -> User | None:
    """Create or return the dev user for local development.

    Uses the dev user ID to create a stable user per browser/device.
    """
    from sqlmodel import select

    # Convert the header string to a proper UUID for type safety
    try:
        dev_uuid = uuid.UUID(dev_user_id)
    except ValueError:
        # Invalid UUID format in the header — reject
        return None

    # Try to find existing user
    result = await db.execute(select(User).where(User.id == dev_uuid))
    user = result.scalar_one_or_none()

    if user:
        return user

    # Create a new dev user with a deterministic display name
    user = User(
        id=dev_uuid,
        display_name=f"Dev User {dev_user_id[:8]}",
        email=f"dev-{dev_user_id[:8]}@localhost",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
