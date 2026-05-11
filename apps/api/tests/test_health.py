"""Smoke tests for health endpoints and auth."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_client():
    """Async HTTP client pre-set with dev auth header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Dev-User-Id": "00000000-0000-0000-0000-000000000001"},
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /api/v1/health returns 200 with expected fields."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "deadlock-ai-api"
    assert "version" in data


@pytest.mark.asyncio
async def test_upload_validation_rejects_invalid_kind(auth_client: AsyncClient):
    """POST /api/v1/uploads with invalid kind returns 400."""
    response = await auth_client.post(
        "/api/v1/uploads",
        json={"kind": "invalid_kind", "filename": "test.dem"},
    )
    assert response.status_code == 400
    assert "kind must be one of" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_replay_requires_filename(auth_client: AsyncClient):
    """POST /api/v1/uploads with kind=replay and no filename returns 400."""
    response = await auth_client.post(
        "/api/v1/uploads",
        json={"kind": "replay", "size_bytes": 12345},
    )
    assert response.status_code == 400
    assert "filename is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_match_summary_requires_summary_text(auth_client: AsyncClient):
    """POST /api/v1/uploads with kind=match_summary and no summary_text returns 400."""
    response = await auth_client.post(
        "/api/v1/uploads",
        json={"kind": "match_summary"},
    )
    assert response.status_code == 400
    assert "summary_text is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_oversized_payload(auth_client: AsyncClient):
    """POST /api/v1/uploads with size_bytes > 5GB returns 413."""
    response = await auth_client.post(
        "/api/v1/uploads",
        json={
            "kind": "replay",
            "filename": "match.dem",
            "size_bytes": 6 * 1024 * 1024 * 1024,
        },
    )
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient):
    """GET /api/v1/me without auth header returns 401."""
    response = await client.get("/api/v1/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user_info(auth_client: AsyncClient):
    """GET /api/v1/me with dev auth returns user info."""
    response = await auth_client.get("/api/v1/me")

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] == "00000000-0000-0000-0000-000000000001"
    assert data["display_name"] is not None


@pytest.mark.asyncio
async def test_uploads_requires_auth(client: AsyncClient):
    """GET /api/v1/uploads without auth header returns 401."""
    response = await client.get("/api/v1/uploads")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_upload_succeeds_with_auth(auth_client: AsyncClient):
    """POST /api/v1/uploads with valid payload returns 201."""
    response = await auth_client.post(
        "/api/v1/uploads",
        json={
            "kind": "replay",
            "filename": "match.dem",
            "size_bytes": 12345,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["kind"] == "replay"
    assert data["status"] == "created"
    assert data["filename"] == "match.dem"