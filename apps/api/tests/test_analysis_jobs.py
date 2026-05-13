"""Tests for Phase 2 analysis jobs."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import select

from app.db.models import AnalysisJob, AnalysisJobStatus, AnalysisResult, Upload, UploadKind, User
from app.db.session import AsyncSessionLocal
from app.main import app
from app.workers.analysis import process_analysis_job

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000002"


@pytest.fixture
async def auth_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Dev-User-Id": DEV_USER_ID},
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
def fake_enqueue(monkeypatch):
    async def enqueue(_db, upload_id, user):
        from app.services.analysis_jobs import create_and_enqueue_job

        job = await create_and_enqueue_job(_db, upload_id, user)
        job.queue_job_id = "test-arq-job"
        return job

    async def queue_stub(job_id: str) -> str:
        return f"test-arq-{job_id}"

    monkeypatch.setattr("app.services.analysis_jobs.enqueue_analysis_job", queue_stub)


async def create_upload_record(user_id: uuid.UUID) -> uuid.UUID:
    async with AsyncSessionLocal() as db:
        user = await db.get(User, user_id)
        if user is None:
            user = User(id=user_id, display_name="Test User")
            db.add(user)
            await db.flush()
        upload = Upload(user_id=user_id, kind=UploadKind.REPLAY, filename="match.dem")
        db.add(upload)
        await db.commit()
        await db.refresh(upload)
        return upload.id


@pytest.mark.asyncio
async def test_create_analysis_job_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/analysis-jobs",
            json={"upload_id": str(uuid.uuid4())},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_analysis_job_for_owned_upload(auth_client: AsyncClient):
    upload_id = await create_upload_record(uuid.UUID(DEV_USER_ID))

    response = await auth_client.post(
        "/api/v1/analysis-jobs",
        json={"upload_id": str(upload_id)},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["upload_id"] == str(upload_id)
    assert data["status"] == "queued"
    assert data["queue_job_id"].startswith("test-arq-")


@pytest.mark.asyncio
async def test_create_analysis_job_rejects_cross_user_upload(auth_client: AsyncClient):
    upload_id = await create_upload_record(uuid.UUID(OTHER_USER_ID))

    response = await auth_client.post(
        "/api/v1/analysis-jobs",
        json={"upload_id": str(upload_id)},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_analysis_job_rejects_duplicate(auth_client: AsyncClient):
    upload_id = await create_upload_record(uuid.UUID(DEV_USER_ID))
    first = await auth_client.post("/api/v1/analysis-jobs", json={"upload_id": str(upload_id)})
    second = await auth_client.post("/api/v1/analysis-jobs", json={"upload_id": str(upload_id)})

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_result_endpoint_conflicts_before_completion(auth_client: AsyncClient):
    upload_id = await create_upload_record(uuid.UUID(DEV_USER_ID))
    create_response = await auth_client.post(
        "/api/v1/analysis-jobs",
        json={"upload_id": str(upload_id)},
    )
    job_id = create_response.json()["id"]

    response = await auth_client.get(f"/api/v1/analysis-jobs/{job_id}/result")

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_worker_persists_result(auth_client: AsyncClient):
    upload_id = await create_upload_record(uuid.UUID(DEV_USER_ID))
    create_response = await auth_client.post(
        "/api/v1/analysis-jobs",
        json={"upload_id": str(upload_id)},
    )
    job_id = create_response.json()["id"]

    await process_analysis_job({}, job_id)

    response = await auth_client.get(f"/api/v1/analysis-jobs/{job_id}/result")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["schema_version"] == "fake-analysis-v1"
    assert data["payload"]["source"]["upload_id"] == str(upload_id)

    async with AsyncSessionLocal() as db:
        job = await db.get(AnalysisJob, uuid.UUID(job_id))
        assert job is not None
        assert job.status == AnalysisJobStatus.SUCCEEDED
        assert job.progress == 100


@pytest.mark.asyncio
async def test_worker_is_idempotent(auth_client: AsyncClient):
    upload_id = await create_upload_record(uuid.UUID(DEV_USER_ID))
    create_response = await auth_client.post(
        "/api/v1/analysis-jobs",
        json={"upload_id": str(upload_id)},
    )
    job_id = create_response.json()["id"]

    await process_analysis_job({}, job_id)
    await process_analysis_job({}, job_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AnalysisResult).where(AnalysisResult.job_id == uuid.UUID(job_id))
        )
        assert len(result.scalars().all()) == 1
