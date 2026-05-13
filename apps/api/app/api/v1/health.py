"""Health and readiness endpoints."""

import redis.asyncio as redis
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()

# Module-level Redis connection pool — reused across readiness checks
_redis_pool: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """Return a module-level Redis client with a shared connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_pool


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessStatus(BaseModel):
    status: str
    database: str
    redis: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic liveness check.

    Returns 200 if the application process is running.
    """
    return HealthResponse(
        status="ok",
        service="deadlock-ai-api",
        version=settings.app_version,
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_check(response: Response) -> ReadinessStatus:
    """Readiness check — verifies database and Redis connectivity.

    Returns 200 if all dependencies are reachable.
    Returns 503 if any dependency is unavailable.
    """
    db_status = "ok"
    redis_status = "ok"

    # Check database connectivity
    try:
        from sqlalchemy import text

        from app.db.session import async_engine

        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    # Check Redis connectivity — reuses module-level connection pool
    try:
        r = _get_redis()
        await r.ping()
    except Exception as e:
        redis_status = f"error: {e}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessStatus(
        status="ok" if response.status_code == 200 else "degraded",
        database=db_status,
        redis=redis_status,
    )
