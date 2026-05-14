"""Workflow node: load job and upload input."""

from sqlmodel import select

from app.db.models import AnalysisJob, AnalysisJobStatus, AnalysisResult, Upload
from app.services.analysis_jobs import now_utc
from app.workflows.analysis.state import AnalysisWorkflowState, UploadSnapshot, WorkflowNodeResult


async def load_input(db, state: AnalysisWorkflowState) -> tuple[AnalysisJob | None, Upload | None, WorkflowNodeResult]:
    """Load the analysis job and upload, preserving idempotency."""
    result = await db.execute(select(AnalysisJob).where(AnalysisJob.id == state.job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise ValueError("analysis job not found")

    existing_result = await db.execute(select(AnalysisResult).where(AnalysisResult.job_id == state.job_id))
    if job.status == AnalysisJobStatus.SUCCEEDED and existing_result.scalar_one_or_none():
        return job, None, WorkflowNodeResult(state=state, status="skipped", output_metadata={"reason": "already_succeeded"})

    if job.upload_id is None:
        raise ValueError("analysis job has no upload")
    upload_result = await db.execute(select(Upload).where(Upload.id == job.upload_id))
    upload = upload_result.scalar_one_or_none()
    if upload is None:
        raise ValueError("analysis job upload not found")

    job.status = AnalysisJobStatus.RUNNING
    job.progress = 10
    job.attempt_count += 1
    job.error_message = None
    job.started_at = job.started_at or now_utc()
    state.upload = UploadSnapshot(
        id=upload.id,
        kind=str(upload.kind),
        summary_text=upload.summary_text,
        match_id=upload.match_id,
        storage_key=upload.storage_key,
    )
    await db.flush()
    return job, upload, WorkflowNodeResult(state=state, status="succeeded", output_metadata={"upload_kind": str(upload.kind)})
