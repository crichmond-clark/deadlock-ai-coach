"""Replay parse artifact endpoints."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import resolve_current_user
from app.db.models import User
from app.db.session import get_db
from app.services.replay_artifacts import get_owned_replay_artifact

router = APIRouter()

CurrentUser = Annotated[User, Depends(resolve_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


class ReplayParseArtifactResponse(BaseModel):
    id: str
    job_id: str | None
    upload_id: str
    parser_name: str
    parser_version: str | None
    schema_version: str
    status: str
    artifact: dict[str, Any] | None
    warnings: list[str]
    error_message: str | None
    parse_duration_ms: int | None
    created_at: datetime


@router.get("/analysis-jobs/{job_id}/replay-artifact", response_model=ReplayParseArtifactResponse)
async def get_replay_artifact(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ReplayParseArtifactResponse:
    artifact = await get_owned_replay_artifact(db, job_id, current_user)
    return ReplayParseArtifactResponse(
        id=str(artifact.id),
        job_id=str(artifact.job_id) if artifact.job_id else None,
        upload_id=str(artifact.upload_id),
        parser_name=artifact.parser_name,
        parser_version=artifact.parser_version,
        schema_version=artifact.schema_version,
        status=artifact.status,
        artifact=artifact.artifact,
        warnings=artifact.warnings,
        error_message=artifact.error_message,
        parse_duration_ms=artifact.parse_duration_ms,
        created_at=artifact.created_at,
    )
