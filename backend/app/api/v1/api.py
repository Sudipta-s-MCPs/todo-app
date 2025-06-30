"""
Main API v1 router
Created: 2025-01-30 14:18:00 PST
"""

from fastapi import APIRouter

from app.api.v1 import auth, workspaces, tasks

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(tasks.router, prefix="", tags=["tasks"])  # Tasks routes are prefixed in the endpoint definitions