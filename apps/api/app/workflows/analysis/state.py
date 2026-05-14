"""Typed analysis workflow state and node results."""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.ai_analysis import CoachingAnalysisResult
from app.schemas.enriched_match import EnrichedMatchContext
from app.schemas.retrieval import RetrievalContext

WorkflowStepStatus = Literal["succeeded", "failed", "skipped"]


class UploadSnapshot(BaseModel):
    """Safe upload fields needed by the workflow."""

    id: uuid.UUID
    kind: str
    summary_text: str | None = None
    match_id: int | None = None
    storage_key: str | None = None


class WorkflowWarning(BaseModel):
    """Recoverable workflow warning."""

    code: str
    message: str
    step_name: str
    recoverable: bool = True


class WorkflowError(BaseModel):
    """Safe workflow error snapshot."""

    code: str
    message: str
    step_name: str | None = None


class AnalysisWorkflowState(BaseModel):
    """Serializable analysis workflow state."""

    workflow_run_id: uuid.UUID
    job_id: uuid.UUID
    user_id: uuid.UUID
    upload: UploadSnapshot | None = None
    replay_artifact_id: uuid.UUID | None = None
    replay_parse_summary: dict[str, Any] | None = None
    enriched_context: EnrichedMatchContext | None = None
    retrieval_context: RetrievalContext | None = None
    ai_result: CoachingAnalysisResult | None = None
    analysis_result_id: uuid.UUID | None = None
    warnings: list[WorkflowWarning] = Field(default_factory=list)
    fatal_error: WorkflowError | None = None

    def safe_snapshot(self) -> dict[str, Any]:
        """Return a compact snapshot safe for telemetry storage."""
        data = self.model_dump(mode="json", exclude={"ai_result"})
        upload = data.get("upload")
        if isinstance(upload, dict) and upload.get("summary_text"):
            upload["summary_text"] = "[redacted]"
        return data


class WorkflowNodeResult(BaseModel):
    """Result returned by workflow nodes."""

    state: AnalysisWorkflowState
    status: WorkflowStepStatus
    warnings: list[WorkflowWarning] = Field(default_factory=list)
    output_metadata: dict[str, Any] = Field(default_factory=dict)
