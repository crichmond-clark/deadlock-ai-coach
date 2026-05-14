"""Arq analysis worker task implementation."""

import uuid

from sqlmodel import select

from app.core.config import settings
from app.db.models import AnalysisJob, AnalysisJobStatus, AnalysisResult, Upload, UploadKind
from app.db.session import get_db_context
from app.services.ai_analysis import generate_structured_analysis
from app.services.analysis_jobs import mark_job_failed, now_utc
from app.services.deadlock_api.enrichment import enrich_match_context
from app.services.fake_analysis import build_fake_analysis_payload
from app.services.replay_artifacts import create_succeeded_artifact, parse_summary
from app.services.replay_parser import parse_replay_file, resolve_local_replay_path


async def process_analysis_job(ctx: dict, job_id: str) -> None:
    """Process one queued analysis job."""
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

            replay_artifact = None
            replay_parse_summary = None
            enriched_context = None
            if upload.kind == UploadKind.REPLAY:
                replay_path = resolve_local_replay_path(upload.storage_key)
                if replay_path is not None and settings.replay_parser_command:
                    parse_result = await parse_replay_file(replay_path, max_events=settings.replay_parser_max_events)
                    replay_artifact = await create_succeeded_artifact(db, job, parse_result)
                    replay_parse_summary = parse_summary(parse_result)
                    job.progress = 50
                    await db.flush()

                    # Enrichment: combine replay artifact with Deadlock API data
                    try:
                        enriched_context = await enrich_match_context(
                            db,
                            replay_artifact_id=replay_artifact.id,
                            match_id=parse_result.match.get("match_id"),
                        )
                    except Exception:
                        enriched_context = None
                    job.progress = 55
                    await db.flush()

            elif upload.kind == UploadKind.MATCH_ID and upload.match_id is not None:
                job.progress = 40
                await db.flush()
                try:
                    enriched_context = await enrich_match_context(
                        db,
                        match_id=upload.match_id,
                    )
                except Exception:
                    enriched_context = None
                job.progress = 55
                await db.flush()

            if settings.analysis_mode == "ai":
                structured_result = await generate_structured_analysis(
                    db,
                    job=job,
                    upload=upload,
                    replay_artifact=replay_artifact,
                    enriched_context=enriched_context,
                    replay_parse_summary=replay_parse_summary,
                )
                payload = structured_result.model_dump(mode="json")
                result_kind = "structured_ai_analysis"
                schema_version = structured_result.schema_version
                title = structured_result.title
                summary = structured_result.summary
            else:
                payload = build_fake_analysis_payload(upload, replay_parse_summary)
                if replay_artifact is not None:
                    payload["source"].update(
                        {
                            "replay_artifact_id": str(replay_artifact.id),
                            "replay_schema_version": replay_artifact.schema_version,
                            "parser_name": replay_artifact.parser_name,
                        }
                    )
                if enriched_context is not None:
                    payload["enriched_context"] = enriched_context.model_dump()
                result_kind = "fake_analysis"
                schema_version = "fake-analysis-v1"
                title = payload["title"]
                summary = payload["summary"]
            job.progress = 60
            await db.flush()

            analysis_result = AnalysisResult(
                user_id=job.user_id,
                job_id=job.id,
                upload_id=job.upload_id,
                result_kind=result_kind,
                schema_version=schema_version,
                title=title,
                summary=summary,
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
