"""Workflow node: parse replay uploads when configured."""

from app.core.config import settings
from app.db.models import UploadKind
from app.services.replay_artifacts import create_succeeded_artifact, parse_summary
from app.services.replay_parser import parse_replay_file, resolve_local_replay_path
from app.workflows.analysis.state import AnalysisWorkflowState, WorkflowNodeResult, WorkflowWarning


async def parse_replay_if_needed(db, state: AnalysisWorkflowState, job, upload) -> tuple[object | None, WorkflowNodeResult]:
    """Parse replay uploads, skipping safely when no local parser/input exists."""
    if upload.kind != UploadKind.REPLAY:
        return None, WorkflowNodeResult(state=state, status="skipped", output_metadata={"reason": "not_replay"})

    replay_path = resolve_local_replay_path(upload.storage_key)
    if replay_path is None or not settings.replay_parser_command:
        warning = WorkflowWarning(
            code="replay_parser_unavailable",
            message="Replay parser command or local replay path is not configured",
            step_name="parse_replay_if_needed",
        )
        state.warnings.append(warning)
        return None, WorkflowNodeResult(state=state, status="skipped", warnings=[warning])

    parse_result = await parse_replay_file(replay_path, max_events=settings.replay_parser_max_events)
    artifact = await create_succeeded_artifact(db, job, parse_result)
    state.replay_artifact_id = artifact.id
    state.replay_parse_summary = parse_summary(parse_result)
    job.progress = 50
    await db.flush()
    return artifact, WorkflowNodeResult(state=state, status="succeeded", output_metadata={"artifact_id": str(artifact.id)})
