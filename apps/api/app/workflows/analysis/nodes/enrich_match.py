"""Workflow node: enrich match context from Deadlock API."""

from app.core.config import settings
from app.db.models import UploadKind
from app.services.deadlock_api.enrichment import enrich_match_context
from app.workflows.analysis.state import AnalysisWorkflowState, WorkflowNodeResult, WorkflowWarning


async def enrich_match_if_enabled(db, state: AnalysisWorkflowState, upload, replay_artifact, parse_result_match_id=None) -> WorkflowNodeResult:
    """Enrich match context, degrading to a warning on external API failure."""
    if not settings.enable_deadlock_api_enrichment:
        return WorkflowNodeResult(state=state, status="skipped", output_metadata={"reason": "disabled"})

    match_id = parse_result_match_id
    if upload.kind == UploadKind.MATCH_ID:
        match_id = upload.match_id
    elif state.replay_parse_summary:
        match = state.replay_parse_summary.get("match")
        if isinstance(match, dict):
            match_id = match.get("match_id")

    if replay_artifact is None and match_id is None:
        return WorkflowNodeResult(state=state, status="skipped", output_metadata={"reason": "no_match_context"})

    try:
        state.enriched_context = await enrich_match_context(
            db,
            replay_artifact_id=getattr(replay_artifact, "id", None),
            match_id=match_id,
        )
    except Exception as exc:
        warning = WorkflowWarning(
            code="enrichment_failed",
            message=str(exc)[:300] or exc.__class__.__name__,
            step_name="enrich_match_context",
        )
        state.warnings.append(warning)
        return WorkflowNodeResult(state=state, status="failed", warnings=[warning], output_metadata={"non_fatal": True})

    await db.flush()
    return WorkflowNodeResult(state=state, status="succeeded", output_metadata={"source_mode": state.enriched_context.source_mode})
