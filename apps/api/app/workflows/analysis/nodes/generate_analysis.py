"""Workflow node: generate structured coaching analysis with provider fallback."""

from dataclasses import dataclass

from app.core.config import settings
from app.services.ai_analysis import generate_structured_analysis
from app.workflows.analysis.state import AnalysisWorkflowState, WorkflowNodeResult, WorkflowWarning


@dataclass(frozen=True)
class ProviderAttempt:
    """One AI provider/model attempt."""

    provider: str
    model: str


def parse_provider_fallbacks(raw: str, *, primary_provider: str, primary_model: str) -> list[ProviderAttempt]:
    """Parse provider:model fallback entries, primary first."""
    attempts = [ProviderAttempt(primary_provider, primary_model)]
    for item in [part.strip() for part in raw.split(",") if part.strip()]:
        provider, _, model = item.partition(":")
        if provider and model:
            attempt = ProviderAttempt(provider=provider, model=model)
            if attempt not in attempts:
                attempts.append(attempt)
    return attempts


async def generate_analysis_with_fallback(db, state: AnalysisWorkflowState, job, upload, replay_artifact) -> WorkflowNodeResult:
    """Generate structured analysis, trying configured fallback providers."""
    attempts = parse_provider_fallbacks(
        settings.ai_provider_fallbacks,
        primary_provider=settings.ai_provider,
        primary_model=settings.ai_model,
    )
    failures: list[str] = []
    for attempt in attempts:
        try:
            state.ai_result = await generate_structured_analysis(
                db,
                job=job,
                upload=upload,
                replay_artifact=replay_artifact,
                enriched_context=state.enriched_context,
                replay_parse_summary=state.replay_parse_summary,
                retrieval_context=state.retrieval_context,
                provider_name=attempt.provider,
                model_name=attempt.model,
            )
            if failures:
                warning = WorkflowWarning(
                    code="ai_provider_fallback_used",
                    message="Structured analysis succeeded after provider fallback",
                    step_name="generate_structured_analysis",
                )
                state.warnings.append(warning)
                return WorkflowNodeResult(state=state, status="succeeded", warnings=[warning], output_metadata={"provider": attempt.provider})
            return WorkflowNodeResult(state=state, status="succeeded", output_metadata={"provider": attempt.provider})
        except Exception as exc:
            failures.append(f"{attempt.provider}:{attempt.model}: {str(exc)[:200]}")

    raise RuntimeError("all AI provider attempts failed: " + "; ".join(failures))
