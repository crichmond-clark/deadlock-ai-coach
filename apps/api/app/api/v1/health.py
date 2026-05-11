"""Health and readiness endpoints."""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


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

    # Check Redis connectivity
    try:
        import redis.asyncio as redis

        from app.core.config import settings
        r = redis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
    except Exception as e:
        redis_status = f"error: {e}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessStatus(
        status="ok" if response.status_code == 200 else "degraded",
        database=db_status,
        redis=redis_status,
    )
