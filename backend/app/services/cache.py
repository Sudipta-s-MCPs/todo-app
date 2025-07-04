"""
Redis cache service
Created: 2025-01-30 19:00:00 PST
Updated: 2025-07-04 21:30:00 IST - Added proper logging and connection handling
"""

from typing import Optional, Any, List, Dict
import json
import redis.asyncio as redis
from datetime import timedelta
import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache service for session management and caching"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._connection_attempts = 0
        self._max_retries = 3
        self._retry_delay = 1
    
    async def connect(self) -> bool:
        """Connect to Redis with retry logic"""
        for attempt in range(self._max_retries):
            try:
                logger.info(f"Attempting to connect to Redis (attempt {attempt + 1}/{self._max_retries})")
                logger.info(f"Redis URL: {self._sanitize_url(str(settings.REDIS_URL))}")
                
                self.redis_client = await redis.from_url(
                    str(settings.REDIS_URL),
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                # Test the connection
                await self.redis_client.ping()
                logger.info("Successfully connected to Redis")
                return True
                
            except redis.ConnectionError as e:
                logger.error(f"Redis connection error (attempt {attempt + 1}): {str(e)}")
                self.redis_client = None
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected error connecting to Redis: {type(e).__name__}: {str(e)}")
                self.redis_client = None
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
        
        logger.error(f"Failed to connect to Redis after {self._max_retries} attempts")
        return False
    
    def _sanitize_url(self, url: str) -> str:
        """Sanitize Redis URL for logging"""
        # Hide password if present
        if "@" in url:
            parts = url.split("@")
            if ":" in parts[0]:
                scheme_user = parts[0].split(":")
                return f"{scheme_user[0]}:****@{parts[1]}"
        return url
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            try:
                await self.redis_client.aclose()  # Use aclose() for newer redis versions
                logger.info("Disconnected from Redis")
            except Exception as e:
                logger.error(f"Error disconnecting from Redis: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection lost during get operation: {e}")
            self.redis_client = None
            return None
        except Exception as e:
            logger.error(f"Redis get error for key '{key}': {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: Optional[int] = None
    ) -> bool:
        """Set value in cache with optional expiration (in seconds)"""
        if not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value)
            if expire:
                await self.redis_client.setex(key, expire, serialized)
            else:
                await self.redis_client.set(key, serialized)
            return True
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection lost during set operation: {e}")
            self.redis_client = None
            return False
        except Exception as e:
            logger.error(f"Redis set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection lost during delete operation: {e}")
            self.redis_client = None
            return False
        except Exception as e:
            logger.error(f"Redis delete error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection lost during exists operation: {e}")
            self.redis_client = None
            return False
        except Exception as e:
            logger.error(f"Redis exists error for key '{key}': {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key"""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.expire(key, seconds)
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection lost during expire operation: {e}")
            self.redis_client = None
            return False
        except Exception as e:
            logger.error(f"Redis expire error for key '{key}': {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        if not self.redis_client:
            return None
        
        try:
            return await self.redis_client.incrby(key, amount)
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection lost during increment operation: {e}")
            self.redis_client = None
            return None
        except Exception as e:
            logger.error(f"Redis increment error for key '{key}': {e}")
            return None
    
    async def get_keys(self, pattern: str) -> list[str]:
        """Get all keys matching pattern"""
        if not self.redis_client:
            return []
        
        try:
            return await self.redis_client.keys(pattern)
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection lost during keys operation: {e}")
            self.redis_client = None
            return []
        except Exception as e:
            logger.error(f"Redis keys error for pattern '{pattern}': {e}")
            return []
    
    async def ping(self) -> bool:
        """Check Redis connection"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.ping()
            return True
        except Exception:
            return False


# Global Redis cache instance
redis_cache = RedisCache()

# Function to get the current redis client
def get_redis_client():
    """Get the current Redis client instance"""
    return redis_cache.redis_client


# Helper functions for common cache operations
async def cache_user_session(
    user_id: str, 
    session_id: str, 
    session_data: dict,
    expire_minutes: int = 30
) -> bool:
    """Cache user session data"""
    key = f"session:{user_id}:{session_id}"
    return await redis_cache.set(key, session_data, expire_minutes * 60)


async def get_user_session(user_id: str, session_id: str) -> Optional[dict]:
    """Get user session data from cache"""
    key = f"session:{user_id}:{session_id}"
    return await redis_cache.get(key)


async def invalidate_user_session(user_id: str, session_id: str) -> bool:
    """Invalidate user session"""
    key = f"session:{user_id}:{session_id}"
    return await redis_cache.delete(key)


async def cache_api_response(
    endpoint: str,
    params: dict,
    response_data: Any,
    expire_seconds: int = 300
) -> bool:
    """Cache API response"""
    key = f"api:{endpoint}:{hash(frozenset(params.items()))}"
    return await redis_cache.set(key, response_data, expire_seconds)


async def get_cached_api_response(
    endpoint: str,
    params: dict
) -> Optional[Any]:
    """Get cached API response"""
    key = f"api:{endpoint}:{hash(frozenset(params.items()))}"
    return await redis_cache.get(key)


# Rate limiting helpers
async def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int
) -> tuple[bool, int]:
    """
    Check if rate limit is exceeded
    Returns: (is_allowed, remaining_requests)
    """
    if not redis_cache.redis_client:
        logger.debug("Redis unavailable for rate limiting")
        return True, max_requests
    
    try:
        current = await redis_cache.increment(key)
        if current == 1:
            # First request, set expiration
            await redis_cache.expire(key, window_seconds)
        
        if current is None:
            return True, max_requests
        
        remaining = max(0, max_requests - current)
        is_allowed = current <= max_requests
        
        return is_allowed, remaining
    except Exception as e:
        logger.error(f"Rate limit check failed for key '{key}': {e}")
        # On error, allow the request but log the issue
        return True, max_requests