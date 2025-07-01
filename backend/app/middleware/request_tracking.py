"""
Request tracking middleware
Created: 2025-01-30 20:45:00 PST
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import uuid

from app.utils.logging import get_request_logger, performance_logger


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Track and log all requests"""
    
    async def dispatch(self, request: Request, call_next):
        """Track request lifecycle"""
        # Skip tracking for health checks
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Get logger with request context
        logger = get_request_logger(request, __name__)
        
        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "query_params": dict(request.query_params),
                "headers": self._get_safe_headers(request)
            }
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add tracking headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        
        # Log request completion
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "status_code": response.status_code,
                "duration": duration
            }
        )
        
        # Log slow requests
        performance_logger.log_slow_request(
            method=request.method,
            path=request.url.path,
            duration=duration,
            status_code=response.status_code,
            threshold=1.0
        )
        
        return response
    
    def _get_safe_headers(self, request: Request) -> dict:
        """Get headers with sensitive values masked"""
        safe_headers = {}
        sensitive_headers = [
            "authorization", "x-api-key", "cookie", 
            "x-signature", "x-auth-token"
        ]
        
        for header, value in request.headers.items():
            if header.lower() in sensitive_headers:
                safe_headers[header] = "***MASKED***"
            else:
                safe_headers[header] = value
        
        return safe_headers