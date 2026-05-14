"""Persistence helpers for replay parse artifacts."""

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models import AnalysisJob, AnalysisJobStatus, ReplayParseArtifact, User
from app.services.replay_parser import ReplayParseResult


def parse_summary(result: ReplayParseResult) -> dict[str, Any]:
    return {
        "duration_seconds": result.match.get("duration_seconds"),
        "players_count": len(result.players),
        "timeline_events_count": len(result.timeline),
        "warnings_count": len(result.warnings),
    }


async def create_succeeded_artifact(
    db: AsyncSession,
    job: AnalysisJob,
    result: ReplayParseResult,
) -> ReplayParseArtifact:
    parser = result.parser
    stats = result.stats
    artifact = ReplayParseArtifact(
        user_id=job.user_id,
        upload_id=job.upload_id,
        job_id=job.id,
        parser_name=str(parser.get("name") or "clarity"),
        parser_version=parser.get("version"),
        schema_version=result.schema_version,
        status="succeeded",
        artifact=result.model_dump(),
        warnings=result.warnings,
        parse_duration_ms=stats.get("parse_duration_ms"),
    )
    db.add(artifact)
    await db.flush()
    return artifact


async def get_owned_replay_artifact(
    db: AsyncSession,
    job_id: uuid.UUID,
    user: User,
) -> ReplayParseArtifact:
    job = await db.get(AnalysisJob, job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="replay artifact not found")
    if job.status in {AnalysisJobStatus.QUEUED, AnalysisJobStatus.RUNNING}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="analysis job is not complete")

    result = await db.execute(select(ReplayParseArtifact).where(ReplayParseArtifact.job_id == job_id))
    artifact = result.scalar_one_or_none()
    if artifact is None or artifact.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="replay artifact not found")
    return artifact
