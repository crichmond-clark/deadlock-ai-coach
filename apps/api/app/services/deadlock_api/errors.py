"""Normalized exception types for Deadlock API interactions."""


class DeadlockApiError(Exception):
    """Base error for Deadlock API failures."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DeadlockApiClientError(DeadlockApiError):
    """Client error (4xx) from Deadlock API — invalid request or resource missing."""


class DeadlockApiNotFoundError(DeadlockApiClientError):
    """404 — requested resource was not found."""


class DeadlockApiRateLimitError(DeadlockApiError):
    """429 — rate limit exceeded.  Retry-After header payload is captured."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class DeadlockApiServerError(DeadlockApiError):
    """Server error (5xx) from Deadlock API — upstream is unhealthy."""


class DeadlockApiTimeoutError(DeadlockApiError):
    """API request timed out."""


class DeadlockApiInvalidResponseError(DeadlockApiError):
    """API returned a response that could not be parsed or validated."""
