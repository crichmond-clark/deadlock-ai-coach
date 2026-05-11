"""API v1 router — aggregates all v1 sub-routers."""

from fastapi import APIRouter

from app.api.v1 import health, me, uploads

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(me.router, tags=["Auth"])
api_router.include_router(uploads.router, tags=["Uploads"])
