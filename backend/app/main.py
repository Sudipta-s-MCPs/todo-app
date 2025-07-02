"""
Main FastAPI application
Created: 2025-01-30 13:50:00 PST
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.database import init_db, close_db
from app.utils.logging import setup_logging, get_logger

# Configure logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    logger.info("Starting Smart-ToDo application...")
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Redis cache
    from app.services.cache import redis_cache
    await redis_cache.connect()
    logger.info("Redis cache initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Smart-ToDo application...")
    await close_db()
    logger.info("Database connections closed")
    
    # Disconnect Redis
    await redis_cache.disconnect()
    logger.info("Redis disconnected")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security middleware
from app.middleware import (
    SecurityHeadersMiddleware,
    RequestValidationMiddleware,
    RateLimitMiddleware,
    AuditLogMiddleware,
    IPWhitelistMiddleware,
    ErrorHandlerMiddleware,
    setup_error_handlers,
    RequestTrackingMiddleware
)

# Add security headers
if settings.ENABLE_SECURITY_HEADERS:
    app.add_middleware(SecurityHeadersMiddleware)

# Add request validation
if settings.ENABLE_REQUEST_VALIDATION:
    app.add_middleware(RequestValidationMiddleware)

# Add rate limiting
if settings.ENABLE_RATE_LIMITING:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        requests_per_hour=settings.RATE_LIMIT_PER_HOUR,
        burst_size=settings.RATE_LIMIT_BURST
    )

# Add audit logging
if settings.ENABLE_AUDIT_LOGGING:
    app.add_middleware(AuditLogMiddleware)

# Add IP whitelist for admin endpoints
if settings.ADMIN_IP_WHITELIST:
    app.add_middleware(
        IPWhitelistMiddleware,
        whitelist=settings.ADMIN_IP_WHITELIST
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "smart-todo-backend"
        }
    )


# Include API routers
from app.api.v1.api import api_router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# Include WebSocket endpoint
from app.websockets import websocket_endpoint
app.add_api_websocket_route("/ws", websocket_endpoint)

# Setup error handlers
setup_error_handlers(app)

# Add error handler middleware
app.add_middleware(ErrorHandlerMiddleware)

# Add request tracking
app.add_middleware(RequestTrackingMiddleware)