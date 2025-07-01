"""
Global error handler middleware
Created: 2025-01-30 20:30:00 PST
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import traceback
import uuid

from app.utils.logging import get_request_logger, security_logger
from app.config import settings


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware"""
    
    async def dispatch(self, request: Request, call_next):
        """Handle errors globally"""
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            return await self._handle_error(request, exc)
    
    async def _handle_error(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle different types of errors"""
        logger = get_request_logger(request, __name__)
        
        # Validation errors
        if isinstance(exc, RequestValidationError):
            logger.warning(f"Validation error: {exc.errors()}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": "Invalid request data",
                    "errors": exc.errors(),
                    "request_id": request.state.request_id
                }
            )
        
        # HTTP exceptions
        if isinstance(exc, StarletteHTTPException):
            # Log 5xx errors
            if exc.status_code >= 500:
                logger.error(
                    f"HTTP {exc.status_code} error: {exc.detail}",
                    exc_info=True
                )
            else:
                logger.info(f"HTTP {exc.status_code}: {exc.detail}")
            
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "detail": exc.detail,
                    "request_id": request.state.request_id
                }
            )
        
        # Database errors
        if "sqlalchemy" in str(type(exc).__module__):
            logger.error(f"Database error: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": "Database operation failed",
                    "request_id": request.state.request_id
                }
            )
        
        # Unhandled errors
        logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
        
        # Log security-relevant errors
        if "permission" in str(exc).lower() or "forbidden" in str(exc).lower():
            security_logger.log_suspicious_activity(
                ip_address=request.client.host if request.client else "unknown",
                activity_type="unauthorized_access_attempt",
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(exc)
                }
            )
        
        # In production, don't expose internal errors
        if settings.ENVIRONMENT == "production":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal error occurred",
                    "request_id": request.state.request_id
                }
            )
        else:
            # In development, include error details
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": str(exc),
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc().split("\n"),
                    "request_id": request.state.request_id
                }
            )


def setup_error_handlers(app):
    """Setup FastAPI error handlers"""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        logger = get_request_logger(request, __name__)
        logger.warning(f"Validation error: {exc.errors()}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Invalid request data",
                "errors": exc.errors(),
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions"""
        logger = get_request_logger(request, __name__)
        
        if exc.status_code >= 500:
            logger.error(f"HTTP {exc.status_code} error: {exc.detail}")
        elif exc.status_code == 404:
            logger.debug(f"Not found: {request.url.path}")
        else:
            logger.info(f"HTTP {exc.status_code}: {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unhandled exceptions"""
        logger = get_request_logger(request, __name__)
        logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
        
        # Don't expose internal errors in production
        if settings.ENVIRONMENT == "production":
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "An internal error occurred",
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": str(exc),
                    "type": type(exc).__name__,
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            )