"""Arq analysis worker task implementation."""

import uuid

from sqlmodel import select

from app.db.models import AnalysisJob, AnalysisJobStatus, AnalysisResult, Upload
from app.db.session import get_db_context
from app.services.analysis_jobs import mark_job_failed, now_utc
from app.services.fake_analysis import build_fake_analysis_payload


async def process_analysis_job(ctx: dict, job_id: str) -> None:
    """Process one queued analysis job with deterministic fake analysis."""
    del ctx
    parsed_job_id = uuid.UUID(job_id)

    async with get_db_context() as db:
        result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == parsed_job_id))
        job = result.scalar_one_or_none()
        if job is None:
            return

        existing_result = await db.execute(
            select(AnalysisResult).where(AnalysisResult.job_id == parsed_job_id)
        )
        if job.status == AnalysisJobStatus.SUCCEEDED and existing_result.scalar_one_or_none():
            return

        try:
            upload = await load_upload(db, job)
            job.status = AnalysisJobStatus.RUNNING
            job.progress = 10
            job.attempt_count += 1
            job.error_message = None
            job.started_at = job.started_at or now_utc()
            await db.flush()

            payload = build_fake_analysis_payload(upload)
            job.progress = 60
            await db.flush()

            analysis_result = AnalysisResult(
                user_id=job.user_id,
                job_id=job.id,
                upload_id=job.upload_id,
                title=payload["title"],
                summary=payload["summary"],
                payload=payload,
            )
            db.add(analysis_result)
            job.status = AnalysisJobStatus.SUCCEEDED
            job.progress = 100
            job.completed_at = now_utc()
            await db.flush()
        except Exception as exc:
            await mark_job_failed(db, job, exc)
            raise


async def load_upload(db, job: AnalysisJob) -> Upload:
    if job.upload_id is None:
        raise ValueError("analysis job has no upload")
    result = await db.execute(select(Upload).where(Upload.id == job.upload_id))
    upload = result.scalar_one_or_none()
    if upload is None:
        raise ValueError("analysis job upload not found")
    return upload
