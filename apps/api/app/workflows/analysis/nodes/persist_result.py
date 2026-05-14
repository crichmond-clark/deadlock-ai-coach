"""Workflow node: persist final AnalysisResult."""

from sqlmodel import select

from app.db.models import AnalysisResult
from app.workflows.analysis.state import AnalysisWorkflowState, WorkflowNodeResult


async def persist_analysis_result(db, state: AnalysisWorkflowState, job) -> WorkflowNodeResult:
    """Persist the workflow's final structured AI result."""
    if state.ai_result is None:
        raise ValueError("workflow has no AI result to persist")

    existing_result = await db.execute(select(AnalysisResult).where(AnalysisResult.job_id == job.id))
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        state.analysis_result_id = existing.id
        return WorkflowNodeResult(state=state, status="skipped", output_metadata={"reason": "result_exists"})

    payload = state.ai_result.model_dump(mode="json")
    result = AnalysisResult(
        user_id=job.user_id,
        job_id=job.id,
        upload_id=job.upload_id,
        result_kind="structured_ai_analysis",
        schema_version=state.ai_result.schema_version,
        title=state.ai_result.title,
        summary=state.ai_result.summary,
        payload=payload,
    )
    db.add(result)
    await db.flush()
    state.analysis_result_id = result.id
    return WorkflowNodeResult(state=state, status="succeeded", output_metadata={"result_id": str(result.id)})
