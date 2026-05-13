"""Analysis job endpoints."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import resolve_current_user
from app.db.models import AnalysisJob, AnalysisResult, User
from app.db.session import get_db
from app.services.analysis_jobs import (
    create_and_enqueue_job,
    get_completed_result,
    get_job_result,
    get_owned_job,
    list_user_jobs,
)

router = APIRouter()

CurrentUser = Annotated[User, Depends(resolve_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


class AnalysisJobCreateRequest(BaseModel):
    upload_id: uuid.UUID


class AnalysisResultSummary(BaseModel):
    id: str
    title: str
    summary: str
    schema_version: str


class AnalysisJobResponse(BaseModel):
    id: str
    upload_id: str | None
    status: str
    progress: int
    queue_job_id: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    result: AnalysisResultSummary | None = None


class AnalysisJobListResponse(BaseModel):
    jobs: list[AnalysisJobResponse]
    total: int


class AnalysisResultResponse(BaseModel):
    id: str
    job_id: str
    upload_id: str | None
    result_kind: str
    schema_version: str
    title: str
    summary: str
    payload: dict[str, Any]
    created_at: datetime


def result_summary(result: AnalysisResult | None) -> AnalysisResultSummary | None:
    if result is None:
        return None
    return AnalysisResultSummary(
        id=str(result.id),
        title=result.title,
        summary=result.summary,
        schema_version=result.schema_version,
    )


async def serialize_job(db: AsyncSession, job: AnalysisJob) -> AnalysisJobResponse:
    result = await get_job_result(db, job)
    return AnalysisJobResponse(
        id=str(job.id),
        upload_id=str(job.upload_id) if job.upload_id else None,
        status=job.status.value,
        progress=job.progress,
        queue_job_id=job.queue_job_id,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        result=result_summary(result),
    )


def serialize_result(result: AnalysisResult) -> AnalysisResultResponse:
    return AnalysisResultResponse(
        id=str(result.id),
        job_id=str(result.job_id),
        upload_id=str(result.upload_id) if result.upload_id else None,
        result_kind=result.result_kind,
        schema_version=result.schema_version,
        title=result.title,
        summary=result.summary,
        payload=result.payload,
        created_at=result.created_at,
    )


@router.post("/analysis-jobs", response_model=AnalysisJobResponse, status_code=status.HTTP_201_CREATED)
async def create_analysis_job(
    body: AnalysisJobCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> AnalysisJobResponse:
    job = await create_and_enqueue_job(db, body.upload_id, current_user)
    return await serialize_job(db, job)


@router.get("/analysis-jobs", response_model=AnalysisJobListResponse)
async def list_analysis_jobs(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
) -> AnalysisJobListResponse:
    jobs, total = await list_user_jobs(db, current_user, limit, offset)
    return AnalysisJobListResponse(
        jobs=[await serialize_job(db, job) for job in jobs],
        total=total,
    )


@router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobResponse)
async def get_analysis_job(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> AnalysisJobResponse:
    job = await get_owned_job(db, job_id, current_user)
    return await serialize_job(db, job)


@router.get("/analysis-jobs/{job_id}/result", response_model=AnalysisResultResponse)
async def get_analysis_job_result(
    job_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> AnalysisResultResponse:
    job = await get_owned_job(db, job_id, current_user)
    result = await get_completed_result(db, job)
    if result.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="analysis result not found")
    return serialize_result(result)
