"""Analysis job service helpers."""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from app.db.models import AnalysisJob, AnalysisJobStatus, AnalysisResult, Upload, User
from app.queue.client import enqueue_analysis_job

TERMINAL_STATUSES = {
    AnalysisJobStatus.SUCCEEDED,
    AnalysisJobStatus.FAILED,
    AnalysisJobStatus.CANCELLED,
}
ACTIVE_OR_COMPLETE_STATUSES = {
    AnalysisJobStatus.QUEUED,
    AnalysisJobStatus.RUNNING,
    AnalysisJobStatus.SUCCEEDED,
}


def now_utc() -> datetime:
    return datetime.now(UTC)


def safe_error_message(exc: Exception) -> str:
    """Return a short, safe error message for API/user display."""
    message = str(exc).strip() or exc.__class__.__name__
    return message[:500]


async def get_owned_upload(db: AsyncSession, upload_id: uuid.UUID, user: User) -> Upload:
    result = await db.execute(select(Upload).where(Upload.id == upload_id, Upload.user_id == user.id))
    upload = result.scalar_one_or_none()
    if upload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="upload not found")
    return upload


async def ensure_upload_has_no_active_job(db: AsyncSession, upload_id: uuid.UUID, user: User) -> None:
    result = await db.execute(
        select(AnalysisJob).where(
            AnalysisJob.upload_id == upload_id,
            AnalysisJob.user_id == user.id,
            AnalysisJob.status.in_(ACTIVE_OR_COMPLETE_STATUSES),
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="upload already has an active or completed analysis job",
        )


async def create_and_enqueue_job(db: AsyncSession, upload_id: uuid.UUID, user: User) -> AnalysisJob:
    await get_owned_upload(db, upload_id, user)
    await ensure_upload_has_no_active_job(db, upload_id, user)

    job = AnalysisJob(user_id=user.id, upload_id=upload_id)
    db.add(job)
    await db.flush()
    await db.refresh(job)

    try:
        queue_job_id = await enqueue_analysis_job(str(job.id))
    except Exception as exc:
        job.status = AnalysisJobStatus.FAILED
        job.error_message = safe_error_message(exc)
        job.completed_at = now_utc()
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="could not enqueue analysis job",
        ) from exc

    job.queue_job_id = queue_job_id
    await db.flush()
    await db.refresh(job)
    return job


async def list_user_jobs(db: AsyncSession, user: User, limit: int, offset: int) -> tuple[list[AnalysisJob], int]:
    count_result = await db.execute(
        select(func.count()).select_from(AnalysisJob).where(AnalysisJob.user_id == user.id)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(AnalysisJob)
        .where(AnalysisJob.user_id == user.id)
        .order_by(AnalysisJob.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_owned_job(db: AsyncSession, job_id: uuid.UUID, user: User) -> AnalysisJob:
    result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id, AnalysisJob.user_id == user.id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="analysis job not found")
    return job


async def get_job_result(db: AsyncSession, job: AnalysisJob) -> AnalysisResult | None:
    result = await db.execute(select(AnalysisResult).where(AnalysisResult.job_id == job.id))
    return result.scalar_one_or_none()


async def get_completed_result(db: AsyncSession, job: AnalysisJob) -> AnalysisResult:
    result = await get_job_result(db, job)
    if result is None:
        if job.status in TERMINAL_STATUSES:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="analysis result not found")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="analysis job is not complete")
    return result


async def mark_job_failed(db: AsyncSession, job: AnalysisJob, exc: Exception) -> None:
    job.status = AnalysisJobStatus.FAILED
    job.error_message = safe_error_message(exc)
    job.completed_at = now_utc()
    await db.flush()


async def commit_or_rollback(db: AsyncSession) -> None:
    try:
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise
