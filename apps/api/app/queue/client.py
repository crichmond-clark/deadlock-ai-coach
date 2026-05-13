"""Arq queue client wrapper."""

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

ANALYSIS_TASK_NAME = "process_analysis_job"


def get_redis_settings() -> RedisSettings:
    """Build Arq Redis settings from application configuration."""
    return RedisSettings.from_dsn(settings.redis_url)


async def enqueue_analysis_job(job_id: str) -> str | None:
    """Enqueue an analysis job and return the Arq job ID."""
    redis = await create_pool(get_redis_settings())
    try:
        job = await redis.enqueue_job(ANALYSIS_TASK_NAME, job_id)
        return job.job_id if job else None
    finally:
        await redis.close()
