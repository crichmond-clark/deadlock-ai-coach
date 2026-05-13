"""Upload metadata endpoint with real database operations."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.auth.dependencies import resolve_current_user
from app.db.models import Upload, UploadKind, UploadStatus, User
from app.db.session import get_db

router = APIRouter()

MAX_SIZE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB placeholder


class UploadCreateRequest(BaseModel):
    kind: str = Field(..., description="Must be replay, screenshot, or match_summary")
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    storage_key: str | None = None
    summary_text: str | None = None


class UploadCreateResponse(BaseModel):
    id: str
    kind: str
    status: str
    filename: str | None = None
    created_at: datetime


class UploadListResponse(BaseModel):
    uploads: list[UploadCreateResponse]
    total: int


# Dependency injection types for FastAPI
CurrentUser = Annotated[User, Depends(resolve_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/uploads", response_model=UploadCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(
    body: UploadCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> UploadCreateResponse:
    """Create an upload metadata record.

    Requires Authorization header (Bearer token) in production.
    In local development, accepts X-Dev-User-Id header.

    Validation rules:
    - kind must be replay, screenshot, or match_summary
    - match_summary requires summary_text
    - replay/screenshot require filename
    - size_bytes, if provided, must be <= 5GB

    Phase 1 stores metadata only. Real R2 presigned upload flow comes later.
    """
    # Validate kind
    try:
        kind = UploadKind(body.kind)
    except ValueError:
        valid_kinds = ", ".join(e.value for e in UploadKind)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"kind must be one of: {valid_kinds}",
        ) from None

    # Validate summary_text for match_summary
    if kind == UploadKind.MATCH_SUMMARY and not body.summary_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="summary_text is required when kind is match_summary",
        )

    # Validate filename for replay/screenshot
    if kind in (UploadKind.REPLAY, UploadKind.SCREENSHOT) and not body.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="filename is required for replay and screenshot uploads",
        )

    # Validate size
    if body.size_bytes is not None:
        if body.size_bytes < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="size_bytes must be non-negative",
            )
        if body.size_bytes > MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"size_bytes exceeds maximum allowed ({MAX_SIZE_BYTES})",
            )

    # Create the upload record
    upload = Upload(
        user_id=current_user.id,
        kind=kind,
        filename=body.filename,
        content_type=body.content_type,
        size_bytes=body.size_bytes,
        storage_key=body.storage_key,
        summary_text=body.summary_text,
        status=UploadStatus.CREATED,
    )
    db.add(upload)
    await db.flush()
    await db.refresh(upload)

    return UploadCreateResponse(
        id=str(upload.id),
        kind=upload.kind.value,
        status=upload.status.value,
        filename=upload.filename,
        created_at=upload.created_at,
    )


@router.get("/uploads", response_model=UploadListResponse)
async def list_uploads(
    current_user: CurrentUser,
    db: DBSession,
) -> UploadListResponse:
    """List all uploads for the authenticated user.

    Requires Authorization header (Bearer token) in production.
    In local development, accepts X-Dev-User-Id header.
    """
    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(Upload).where(Upload.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    # Get paginated uploads ordered by created_at desc
    result = await db.execute(
        select(Upload)
        .where(Upload.user_id == current_user.id)
        .order_by(Upload.created_at.desc())
        .limit(50)
    )
    uploads = result.scalars().all()

    return UploadListResponse(
        uploads=[
            UploadCreateResponse(
                id=str(u.id),
                kind=u.kind.value,
                status=u.status.value,
                filename=u.filename,
                created_at=u.created_at,
            )
            for u in uploads
        ],
        total=total,
    )
