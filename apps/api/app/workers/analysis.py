"""Arq analysis worker task implementation."""

import uuid

from app.workflows.analysis import run_analysis_workflow


async def process_analysis_job(ctx: dict, job_id: str) -> None:
    """Process one queued analysis job through the analysis workflow."""
    del ctx
    await run_analysis_workflow(uuid.UUID(job_id))
