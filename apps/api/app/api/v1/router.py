"""API v1 router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from app.api.v1 import analysis_jobs, health, me, replay_artifacts, uploads

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(me.router, tags=["Auth"])
api_router.include_router(uploads.router, tags=["Uploads"])
api_router.include_router(analysis_jobs.router, tags=["Analysis Jobs"])
api_router.include_router(replay_artifacts.router, tags=["Replay Artifacts"])
