"""Smoke tests for health endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async HTTP client for testing FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
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
async def test_upload_validation_rejects_invalid_kind(client: AsyncClient):
    """POST /api/v1/uploads with invalid kind returns 422."""
    response = await client.post(
        "/api/v1/uploads",
        json={"kind": "invalid_kind", "filename": "test.dem"},
    )
    # Custom validation returns 400 not 422
    assert response.status_code == 400
    assert "kind must be one of" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_replay_requires_filename(client: AsyncClient):
    """POST /api/v1/uploads with kind=replay and no filename returns 400."""
    response = await client.post(
        "/api/v1/uploads",
        json={"kind": "replay", "size_bytes": 12345},
    )
    assert response.status_code == 400
    assert "filename is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_match_summary_requires_summary_text(client: AsyncClient):
    """POST /api/v1/uploads with kind=match_summary and no summary_text returns 400."""
    response = await client.post(
        "/api/v1/uploads",
        json={"kind": "match_summary"},
    )
    assert response.status_code == 400
    assert "summary_text is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_oversized_payload(client: AsyncClient):
    """POST /api/v1/uploads with size_bytes > 5GB returns 413."""
    response = await client.post(
        "/api/v1/uploads",
        json={
            "kind": "replay",
            "filename": "match.dem",
            "size_bytes": 6 * 1024 * 1024 * 1024,
        },
    )
    assert response.status_code == 413
