"""Arq worker settings."""

from app.queue.client import get_redis_settings
from app.workers.analysis import process_analysis_job


class WorkerSettings:
    """Settings object loaded by `arq app.workers.worker.WorkerSettings`."""

    functions = [process_analysis_job]
    redis_settings = get_redis_settings()
    max_jobs = 5
    job_timeout = 60
