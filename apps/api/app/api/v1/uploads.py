"""Upload metadata endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


class UploadKind(str):
    REPLAY = "replay"
    SCREENSHOT = "screenshot"
    MATCH_SUMMARY = "match_summary"


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


MAX_SIZE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB placeholder


@router.post("/uploads", response_model=UploadCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_upload(body: UploadCreateRequest) -> UploadCreateResponse:
    """Create an upload metadata record.

    Phase 1 stores metadata only. Real R2 presigned upload flow comes later.

    Validation rules:
    - kind must be replay, screenshot, or match_summary
    - match_summary requires summary_text
    - replay/screenshot require filename
    - size_bytes, if provided, must be <= 5GB
    """
    # Validate kind
    valid_kinds = {UploadKind.REPLAY, UploadKind.SCREENSHOT, UploadKind.MATCH_SUMMARY}
    if body.kind not in valid_kinds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"kind must be one of: {', '.join(sorted(valid_kinds))}",
        )

    # Validate summary_text for match_summary
    if body.kind == UploadKind.MATCH_SUMMARY and not body.summary_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="summary_text is required when kind is match_summary",
        )

    # Validate filename for replay/screenshot
    if body.kind in (UploadKind.REPLAY, UploadKind.SCREENSHOT) and not body.filename:
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

    # Return mock response — real DB insert comes in Phase 1D
    return UploadCreateResponse(
        id="00000000-0000-0000-0000-000000000001",
        kind=body.kind,
        status="created",
        filename=body.filename,
        created_at=datetime.now(UTC),
    )
