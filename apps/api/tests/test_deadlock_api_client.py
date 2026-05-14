"""Tests for Deadlock API clients (mocked HTTP)."""

from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from app.services.deadlock_api.client import DeadlockAssetsAPIClient, DeadlockGameAPIClient
from app.services.deadlock_api.errors import (
    DeadlockApiClientError,
    DeadlockApiInvalidResponseError,
    DeadlockApiNotFoundError,
    DeadlockApiRateLimitError,
    DeadlockApiServerError,
    DeadlockApiTimeoutError,
)

MATCH_ID = 44009651
METADATA_URL = f"https://api.deadlock-api.com/v1/matches/{MATCH_ID}/metadata?disable_steam=true"
HERO_ID = 63
HERO_URL = f"https://assets.deadlock-api.com/v2/heroes/{HERO_ID}"


# ── Game API client ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_game_client_get_match_metadata_success(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, json={"match_id": MATCH_ID, "duration_s": 1800})
    client = DeadlockGameAPIClient()
    data = await client.get_match_metadata(MATCH_ID)
    assert data["match_id"] == MATCH_ID
    assert data["duration_s"] == 1800


@pytest.mark.asyncio
async def test_game_client_get_match_metadata_not_found(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, status_code=404, text="not found")
    client = DeadlockGameAPIClient()
    with pytest.raises(DeadlockApiNotFoundError):
        await client.get_match_metadata(MATCH_ID)


@pytest.mark.asyncio
async def test_game_client_rate_limit(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, status_code=429, text="rate limited", headers={"Retry-After": "30"})
    client = DeadlockGameAPIClient()
    with pytest.raises(DeadlockApiRateLimitError) as exc_info:
        await client.get_match_metadata(MATCH_ID)
    assert exc_info.value.retry_after == 30


@pytest.mark.asyncio
async def test_game_client_rate_limit_no_header(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, status_code=429, text="rate limited")
    client = DeadlockGameAPIClient()
    with pytest.raises(DeadlockApiRateLimitError) as exc_info:
        await client.get_match_metadata(MATCH_ID)
    assert exc_info.value.retry_after is None


@pytest.mark.asyncio
async def test_game_client_server_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, status_code=502, text="bad gateway")
    client = DeadlockGameAPIClient()
    with pytest.raises(DeadlockApiServerError):
        await client.get_match_metadata(MATCH_ID)


@pytest.mark.asyncio
async def test_game_client_client_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=METADATA_URL, status_code=400, text="bad request")
    client = DeadlockGameAPIClient()
    with pytest.raises(DeadlockApiClientError):
        await client.get_match_metadata(MATCH_ID)


@pytest.mark.asyncio
async def test_game_client_timeout(httpx_mock: HTTPXMock):
    import httpx as _httpx
    httpx_mock.add_exception(_httpx.TimeoutException("timed out"))
    client = DeadlockGameAPIClient(timeout=0.001)
    with pytest.raises(DeadlockApiTimeoutError):
        await client.get_match_metadata(MATCH_ID)


# ── Assets API client ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assets_client_get_hero_success(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=HERO_URL, json={"hero_id": HERO_ID, "name": "Mina"})
    client = DeadlockAssetsAPIClient()
    data = await client.get_hero(HERO_ID)
    assert data["hero_id"] == HERO_ID
    assert data["name"] == "Mina"


@pytest.mark.asyncio
async def test_assets_client_get_hero_not_found(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=HERO_URL, status_code=404, text="hero not found")
    client = DeadlockAssetsAPIClient()
    with pytest.raises(DeadlockApiNotFoundError):
        await client.get_hero(HERO_ID)


@pytest.mark.asyncio
async def test_assets_client_list_heroes_not_a_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://assets.deadlock-api.com/v2/heroes", json={"error": "bad"})
    client = DeadlockAssetsAPIClient()
    with pytest.raises(DeadlockApiInvalidResponseError, match="expected list of heroes"):
        await client.list_heroes()


@pytest.mark.asyncio
async def test_assets_client_get_item_success(httpx_mock: HTTPXMock):
    url = "https://assets.deadlock-api.com/v2/items/1233782561"
    httpx_mock.add_response(url=url, json={"id": 1233782561, "name": "Love Bites"})
    client = DeadlockAssetsAPIClient()
    data = await client.get_item(1233782561)
    assert data["name"] == "Love Bites"


@pytest.mark.asyncio
async def test_assets_client_rate_limit(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=HERO_URL, status_code=429, text="too many requests")
    client = DeadlockAssetsAPIClient()
    with pytest.raises(DeadlockApiRateLimitError):
        await client.get_hero(HERO_ID)


@pytest.mark.asyncio
async def test_assets_client_server_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=HERO_URL, status_code=503, text="unavailable")
    client = DeadlockAssetsAPIClient()
    with pytest.raises(DeadlockApiServerError):
        await client.get_hero(HERO_ID)


@pytest.mark.asyncio
async def test_assets_client_invalid_json(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=HERO_URL, text="not json")
    client = DeadlockAssetsAPIClient()
    with pytest.raises(DeadlockApiInvalidResponseError):
        await client.get_hero(HERO_ID)
