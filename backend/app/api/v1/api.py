"""
Main API v1 router
Created: 2025-01-30 14:18:00 PST
"""

from fastapi import APIRouter

from app.api.v1 import auth, workspaces, tasks, stats, system, admin, semantic_search, chat, settings

api_router = APIRouter()

# Include all routers
# IMPORTANT: Stats routes must be registered before resource routes to avoid conflicts
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(stats.router, prefix="/stats", tags=["statistics"])  # Stats routes under /stats prefix
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(tasks.router, prefix="", tags=["tasks"])  # Tasks routes are prefixed in the endpoint definitions
api_router.include_router(semantic_search.router, prefix="/search", tags=["semantic search"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])