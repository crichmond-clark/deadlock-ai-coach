"""Thin httpx-based clients for api.deadlock-api.com and assets.deadlock-api.com."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.services.deadlock_api.errors import (
    DeadlockApiClientError,
    DeadlockApiError,
    DeadlockApiInvalidResponseError,
    DeadlockApiNotFoundError,
    DeadlockApiRateLimitError,
    DeadlockApiServerError,
    DeadlockApiTimeoutError,
)

_DEFAULT_HEADERS = {"Accept": "application/json"}


def _auth_headers() -> dict[str, str]:
    if settings.deadlock_api_key:
        return {"Authorization": f"Bearer {settings.deadlock_api_key}"}
    return {}


def _handle_response(response: httpx.Response) -> httpx.Response:
    if response.is_success:
        return response
    status = response.status_code
    message = response.text[:500] or f"status {status}"
    if status == 404:
        raise DeadlockApiNotFoundError(message, status_code=404)
    if status == 429:
        retry_after: int | None = None
        raw = response.headers.get("Retry-After")
        if raw is not None:
            try:
                retry_after = int(raw)
            except ValueError:
                retry_after = None
        raise DeadlockApiRateLimitError(message, retry_after=retry_after)
    if 400 <= status < 500:
        raise DeadlockApiClientError(message, status_code=status)
    if 500 <= status < 600:
        raise DeadlockApiServerError(message, status_code=status)
    raise DeadlockApiServerError(message, status_code=status)


class DeadlockGameAPIClient:
    """Client for https://api.deadlock-api.com (match metadata, analytics)."""

    def __init__(self, *, base_url: str | None = None, timeout: float | None = None) -> None:
        self._base = (base_url or settings.deadlock_api_base_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.deadlock_api_timeout_seconds

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._base}{path}"
        headers = {**_DEFAULT_HEADERS, **_auth_headers()}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=headers, params=params)
                _handle_response(response)
                return response.json()
        except DeadlockApiError:
            raise
        except httpx.TimeoutException:
            raise DeadlockApiTimeoutError(f"timeout requesting {url}") from None
        except httpx.HTTPError as exc:
            raise DeadlockApiServerError(str(exc)[:500]) from exc
        except Exception as exc:
            raise DeadlockApiInvalidResponseError(f"unexpected error: {exc!s}"[:500]) from exc

    async def get_match_metadata(self, match_id: int, *, disable_steam: bool = True) -> dict[str, Any]:
        """Fetch match metadata from GET /v1/matches/{match_id}/metadata."""
        params: dict[str, Any] = {}
        if disable_steam:
            params["disable_steam"] = "true"
        return await self._get(f"/v1/matches/{match_id}/metadata", params=params)

    async def get_player_match_history(self, account_id: int) -> dict[str, Any]:
        """Fetch match history for an account."""
        return await self._get(f"/v1/players/{account_id}/match-history")


class DeadlockAssetsAPIClient:
    """Client for https://assets.deadlock-api.com (heroes, items, abilities)."""

    def __init__(self, *, base_url: str | None = None, timeout: float | None = None) -> None:
        self._base = (base_url or settings.deadlock_assets_api_base_url).rstrip("/")
        self._timeout = timeout if timeout is not None else settings.deadlock_api_timeout_seconds

    async def _get(self, path: str) -> dict[str, Any] | list[dict[str, Any]]:
        url = f"{self._base}{path}"
        headers = {**_DEFAULT_HEADERS, **_auth_headers()}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=headers)
                _handle_response(response)
                return response.json()
        except DeadlockApiError:
            raise
        except httpx.TimeoutException:
            raise DeadlockApiTimeoutError(f"timeout requesting {url}") from None
        except httpx.HTTPError as exc:
            raise DeadlockApiServerError(str(exc)[:500]) from exc
        except Exception as exc:
            raise DeadlockApiInvalidResponseError(f"unexpected error: {exc!s}"[:500]) from exc

    async def list_heroes(self) -> list[dict[str, Any]]:
        """Fetch all heroes from GET /v2/heroes."""
        result = await self._get("/v2/heroes")
        if not isinstance(result, list):
            raise DeadlockApiInvalidResponseError("expected list of heroes")
        return result

    async def get_hero(self, hero_id: int) -> dict[str, Any]:
        """Fetch one hero from GET /v2/heroes/{id}."""
        result = await self._get(f"/v2/heroes/{hero_id}")
        if not isinstance(result, dict):
            raise DeadlockApiInvalidResponseError(f"expected hero object for id {hero_id}")
        return result

    async def list_items(self) -> list[dict[str, Any]]:
        """Fetch all items from GET /v2/items (includes abilities, upgrades)."""
        result = await self._get("/v2/items")
        if not isinstance(result, list):
            raise DeadlockApiInvalidResponseError("expected list of items")
        return result

    async def get_item(self, item_id: int) -> dict[str, Any]:
        """Fetch one item/ability/upgrade from GET /v2/items/{id}."""
        result = await self._get(f"/v2/items/{item_id}")
        if not isinstance(result, dict):
            raise DeadlockApiInvalidResponseError(f"expected item object for id {item_id}")
        return result
