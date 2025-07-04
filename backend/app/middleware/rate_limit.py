"""
Rate limiting middleware
Created: 2025-01-30 19:30:00 PST
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Optional, Callable
import time
import logging

from app.services.cache import check_rate_limit, get_redis_client

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 600,
        burst_size: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Check if Redis is available
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("Redis unavailable - rate limiting disabled")
            # Continue without rate limiting when Redis is unavailable
            return await call_next(request)
        
        # Get client identifier (IP address or authenticated user)
        client_id = self._get_client_id(request)
        
        try:
            # Check burst rate limit (per second)
            burst_key = f"rate_limit:burst:{client_id}"
            burst_allowed, burst_remaining = await check_rate_limit(
                burst_key, self.burst_size, 1
            )
            
            if not burst_allowed:
                logger.info(f"Rate limit exceeded for {client_id} (burst)")
                return self._rate_limit_exceeded_response(request)
            
            # Check minute rate limit
            minute_key = f"rate_limit:minute:{client_id}"
            minute_allowed, minute_remaining = await check_rate_limit(
                minute_key, self.requests_per_minute, 60
            )
            
            if not minute_allowed:
                logger.info(f"Rate limit exceeded for {client_id} (minute)")
                return self._rate_limit_exceeded_response(request)
            
            # Check hourly rate limit
            hour_key = f"rate_limit:hour:{client_id}"
            hour_allowed, hour_remaining = await check_rate_limit(
                hour_key, self.requests_per_hour, 3600
            )
            
            if not hour_allowed:
                logger.info(f"Rate limit exceeded for {client_id} (hour)")
                return self._rate_limit_exceeded_response(request)
        except Exception as e:
            logger.error(f"Error checking rate limits: {e}")
            # If Redis fails during operation, continue without rate limiting
            logger.warning("Rate limiting error - allowing request to proceed")
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers only if we have the data
        try:
            if 'minute_remaining' in locals():
                response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
                response.headers["X-RateLimit-Remaining-Minute"] = str(minute_remaining)
            if 'hour_remaining' in locals():
                response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
                response.headers["X-RateLimit-Remaining-Hour"] = str(hour_remaining)
        except Exception as e:
            logger.debug(f"Could not add rate limit headers: {e}")
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        # Try to get authenticated user ID
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def _rate_limit_exceeded_response(self, request: Request) -> JSONResponse:
        """Return rate limit exceeded response"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded. Please try again later.",
                "type": "rate_limit_exceeded"
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Reset": str(int(time.time()) + 60)
            }
        )


def create_rate_limiter(
    requests_per_minute: int = 60,
    requests_per_hour: int = 600,
    burst_size: int = 10
) -> RateLimitMiddleware:
    """Create rate limiter with specified limits"""
    return RateLimitMiddleware(
        requests_per_minute=requests_per_minute,
        requests_per_hour=requests_per_hour,
        burst_size=burst_size
    )


# Decorators for endpoint-specific rate limiting
def rate_limit(
    requests_per_minute: int = 30,
    key_func: Optional[Callable] = None
):
    """Decorator for endpoint-specific rate limiting"""
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request in args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request found, skip rate limiting
                return await func(*args, **kwargs)
            
            # Get rate limit key
            if key_func:
                key = key_func(request, *args, **kwargs)
            else:
                # Default to IP-based limiting
                client_ip = request.client.host if request.client else "unknown"
                key = f"endpoint:{request.url.path}:{client_ip}"
            
            # Check rate limit
            allowed, remaining = await check_rate_limit(
                key, requests_per_minute, 60
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded for this endpoint"
                )
            
            # Call the actual function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator