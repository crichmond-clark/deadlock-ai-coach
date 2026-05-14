"""Generate and validate structured AI analysis results."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.ai.errors import AISchemaValidationError
from app.ai.providers.base import AIRequestOptions, ChatModelProvider
from app.ai.providers.registry import get_chat_provider
from app.core.config import settings
from app.db.models import AIModelRun, AIModelRunStatus, AnalysisJob, Upload
from app.db.models.replay_parse_artifact import ReplayParseArtifact
from app.schemas.ai_analysis import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    WORKFLOW_VERSION,
    CoachingAnalysisResult,
)
from app.schemas.enriched_match import EnrichedMatchContext
from app.services.ai_analysis.context import build_analysis_input_context
from app.services.ai_analysis.prompts import build_coaching_messages


def _safe_error(exc: Exception) -> str:
    return str(exc)[:1000] or exc.__class__.__name__


async def generate_structured_analysis(
    db,
    *,
    job: AnalysisJob,
    upload: Upload,
    replay_artifact: ReplayParseArtifact | None = None,
    enriched_context: EnrichedMatchContext | None = None,
    replay_parse_summary: dict[str, Any] | None = None,
    provider: ChatModelProvider | None = None,
) -> CoachingAnalysisResult:
    """Call the configured AI provider and return a validated coaching result."""
    selected_provider = provider or get_chat_provider()
    input_context = build_analysis_input_context(
        upload=upload,
        replay_parse_summary=replay_parse_summary,
        enriched_context=enriched_context,
    )
    messages = build_coaching_messages(input_context)
    options = AIRequestOptions(
        model=settings.ai_model,
        temperature=settings.ai_temperature,
        max_output_tokens=settings.ai_max_output_tokens,
        timeout_seconds=settings.ai_timeout_seconds,
    )
    request_metadata = {
        "upload_kind": str(upload.kind),
        "has_replay_artifact": replay_artifact is not None,
        "has_enriched_context": enriched_context is not None,
        "store_raw_prompts": settings.ai_store_raw_prompts,
    }
    if settings.ai_store_raw_prompts:
        request_metadata["messages"] = [message.model_dump() for message in messages]

    model_run = AIModelRun(
        user_id=job.user_id,
        job_id=job.id,
        provider=settings.ai_provider,
        model_name=settings.ai_model,
        prompt_version=PROMPT_VERSION,
        workflow_version=WORKFLOW_VERSION,
        schema_version=SCHEMA_VERSION,
        status=AIModelRunStatus.FAILED,
        request_metadata=request_metadata,
        response_metadata={},
    )
    db.add(model_run)

    try:
        provider_response = await selected_provider.generate_json(
            messages=messages,
            schema_name="CoachingAnalysisResult",
            schema_json=CoachingAnalysisResult.model_json_schema(),
            options=options,
        )
        try:
            result = CoachingAnalysisResult.model_validate(provider_response.content)
        except ValidationError as exc:
            raise AISchemaValidationError(str(exc)[:1000]) from exc

        result.model_metadata.provider = provider_response.provider
        result.model_metadata.model = provider_response.model_name
        model_run.provider = provider_response.provider
        model_run.model_name = provider_response.model_name
        model_run.status = AIModelRunStatus.SUCCEEDED
        model_run.latency_ms = provider_response.latency_ms
        model_run.input_tokens = provider_response.input_tokens
        model_run.output_tokens = provider_response.output_tokens
        model_run.total_tokens = provider_response.total_tokens
        model_run.response_metadata = provider_response.response_metadata
        await db.flush()
        return result
    except Exception as exc:
        model_run.status = AIModelRunStatus.FAILED
        model_run.error_message = _safe_error(exc)
        await db.flush()
        raise
