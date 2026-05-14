"""Deadlock API integration — game API and assets API clients."""

from app.services.deadlock_api.client import DeadlockAssetsAPIClient, DeadlockGameAPIClient
from app.services.deadlock_api.enrichment import enrich_match_context
from app.services.deadlock_api.errors import (
    DeadlockApiClientError,
    DeadlockApiError,
    DeadlockApiInvalidResponseError,
    DeadlockApiNotFoundError,
    DeadlockApiRateLimitError,
    DeadlockApiServerError,
    DeadlockApiTimeoutError,
)

__all__ = [
    "DeadlockApiClientError",
    "DeadlockApiError",
    "DeadlockApiInvalidResponseError",
    "DeadlockApiNotFoundError",
    "DeadlockApiRateLimitError",
    "DeadlockApiServerError",
    "DeadlockApiTimeoutError",
    "DeadlockAssetsAPIClient",
    "DeadlockGameAPIClient",
    "enrich_match_context",
]
