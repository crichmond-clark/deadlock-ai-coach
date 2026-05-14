"""Simple sequential analysis workflow runner."""

import uuid
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import TypeVar

from sqlmodel import select

from app.core.config import settings
from app.db.models import AnalysisJob, AnalysisJobStatus, AnalysisResult, WorkflowRun, WorkflowStep
from app.db.session import get_db_context
from app.services.analysis_jobs import mark_job_failed, now_utc
from app.services.fake_analysis import build_fake_analysis_payload
from app.workflows.analysis.nodes.enrich_match import enrich_match_if_enabled
from app.workflows.analysis.nodes.generate_analysis import generate_analysis_with_fallback
from app.workflows.analysis.nodes.load_input import load_input
from app.workflows.analysis.nodes.parse_replay import parse_replay_if_needed
from app.workflows.analysis.nodes.persist_result import persist_analysis_result
from app.workflows.analysis.nodes.retrieve_strategy import retrieve_strategy_if_enabled
from app.workflows.analysis.state import AnalysisWorkflowState, WorkflowError, WorkflowNodeResult

T = TypeVar("T")


class SimpleAnalysisWorkflowRunner:
    """In-process sequential runner with persisted step telemetry."""

    async def run(self, *, job_id: uuid.UUID) -> AnalysisWorkflowState:
        """Run the analysis workflow for one job ID."""
        async with get_db_context() as db:
            job_lookup = await db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
            initial_job = job_lookup.scalar_one_or_none()
            if initial_job is None:
                raise ValueError("analysis job not found")

            job_result = await db.execute(select(AnalysisResult).where(AnalysisResult.job_id == job_id))
            if job_result.scalar_one_or_none() is not None:
                return AnalysisWorkflowState(workflow_run_id=uuid.uuid4(), job_id=job_id, user_id=initial_job.user_id)

            run = WorkflowRun(
                id=uuid.uuid4(),
                user_id=initial_job.user_id,
                job_id=job_id,
                workflow_version=settings.workflow_version,
                engine=settings.workflow_engine,
                status="running",
            )
            db.add(run)
            await db.flush()
            state = AnalysisWorkflowState(workflow_run_id=run.id, job_id=job_id, user_id=initial_job.user_id)
            started = perf_counter()
            job = None

            try:
                job, upload, load_result = await self._record_step(db, run, "load_input", lambda: load_input(db, state))
                state = load_result.state
                run.user_id = state.user_id = job.user_id
                if load_result.status == "skipped":
                    run.status = "succeeded"
                    run.state_snapshot = state.safe_snapshot()
                    run.completed_at = now_utc()
                    run.duration_ms = _duration_ms(started)
                    await db.flush()
                    return state

                replay_artifact, parse_result = await self._record_step(
                    db,
                    run,
                    "parse_replay_if_needed",
                    lambda: parse_replay_if_needed(db, state, job, upload),
                )
                state = parse_result.state

                enrich_result = await self._record_step(
                    db,
                    run,
                    "enrich_match_context",
                    lambda: enrich_match_if_enabled(db, state, upload, replay_artifact),
                )
                state = enrich_result.state
                job.progress = max(job.progress, 55)

                if settings.analysis_mode == "ai":
                    retrieval_result = await self._record_step(
                        db,
                        run,
                        "retrieve_strategy_context",
                        lambda: retrieve_strategy_if_enabled(db, state),
                    )
                    state = retrieval_result.state
                    job.progress = max(job.progress, 58)

                    generation_result = await self._record_step(
                        db,
                        run,
                        "generate_structured_analysis",
                        lambda: generate_analysis_with_fallback(db, state, job, upload, replay_artifact),
                    )
                    state = generation_result.state
                    persist_result = await self._record_step(
                        db,
                        run,
                        "persist_result",
                        lambda: persist_analysis_result(db, state, job),
                    )
                    state = persist_result.state
                else:
                    await self._record_step(db, run, "persist_result", lambda: self._persist_fake_result(db, state, job, upload, replay_artifact))

                job.status = AnalysisJobStatus.SUCCEEDED
                job.progress = 100
                job.completed_at = now_utc()
                run.status = "succeeded"
                run.completed_at = job.completed_at
                run.duration_ms = _duration_ms(started)
                run.state_snapshot = state.safe_snapshot()
                await db.flush()
                return state
            except Exception as exc:
                if job is not None:
                    await mark_job_failed(db, job, exc)
                run.status = "failed"
                run.completed_at = now_utc()
                run.duration_ms = _duration_ms(started)
                run.error_message = str(exc)[:1000]
                state.fatal_error = WorkflowError(code="workflow_failed", message=str(exc)[:1000])
                run.state_snapshot = state.safe_snapshot()
                await db.flush()
                raise

    async def _record_step(self, db, run: WorkflowRun, name: str, func: Callable[[], Awaitable[T]]) -> T:
        step = WorkflowStep(
            workflow_run_id=run.id,
            step_name=name,
            status="running",
            input_metadata={},
            output_metadata={},
            warnings=[],
        )
        db.add(step)
        await db.flush()
        started = perf_counter()
        try:
            result = await func()
            node_result = _extract_node_result(result)
            step.status = node_result.status if node_result is not None else "succeeded"
            step.output_metadata = node_result.output_metadata if node_result is not None else {}
            step.warnings = [warning.model_dump(mode="json") for warning in node_result.warnings] if node_result else []
            step.completed_at = now_utc()
            step.duration_ms = _duration_ms(started)
            await db.flush()
            return result
        except Exception as exc:
            step.status = "failed"
            step.error_message = str(exc)[:1000]
            step.completed_at = now_utc()
            step.duration_ms = _duration_ms(started)
            await db.flush()
            raise

    async def _persist_fake_result(self, db, state, job, upload, replay_artifact) -> WorkflowNodeResult:
        payload = build_fake_analysis_payload(upload, state.replay_parse_summary)
        if replay_artifact is not None:
            payload["source"].update(
                {
                    "replay_artifact_id": str(replay_artifact.id),
                    "replay_schema_version": replay_artifact.schema_version,
                    "parser_name": replay_artifact.parser_name,
                }
            )
        if state.enriched_context is not None:
            payload["enriched_context"] = state.enriched_context.model_dump()
        if state.retrieval_context is not None:
            payload["retrieval_context"] = state.retrieval_context.model_dump()
        result = AnalysisResult(
            user_id=job.user_id,
            job_id=job.id,
            upload_id=job.upload_id,
            result_kind="fake_analysis",
            schema_version="fake-analysis-v1",
            title=payload["title"],
            summary=payload["summary"],
            payload=payload,
        )
        db.add(result)
        await db.flush()
        state.analysis_result_id = result.id
        return WorkflowNodeResult(state=state, status="succeeded", output_metadata={"result_kind": "fake_analysis"})


def _extract_node_result(result) -> WorkflowNodeResult | None:
    if isinstance(result, WorkflowNodeResult):
        return result
    if isinstance(result, tuple) and result and isinstance(result[-1], WorkflowNodeResult):
        return result[-1]
    return None


def _duration_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)
