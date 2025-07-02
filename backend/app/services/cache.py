"""
Redis cache service
Created: 2025-01-30 19:00:00 PST
"""

from typing import Optional, Any
import json
import redis.asyncio as redis
from datetime import timedelta

from app.config import settings


class RedisCache:
    """Redis cache service for session management and caching"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(
                str(settings.REDIS_URL),
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
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
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on a key"""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.expire(key, seconds)
        except Exception as e:
            print(f"Redis expire error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        if not self.redis_client:
            return None
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"Redis increment error: {e}")
            return None
    
    async def get_keys(self, pattern: str) -> list[str]:
        """Get all keys matching pattern"""
        if not self.redis_client:
            return []
        
        try:
            return await self.redis_client.keys(pattern)
        except Exception as e:
            print(f"Redis keys error: {e}")
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
    current = await redis_cache.increment(key)
    if current == 1:
        # First request, set expiration
        await redis_cache.expire(key, window_seconds)
    
    if current is None:
        return True, max_requests
    
    remaining = max(0, max_requests - current)
    is_allowed = current <= max_requests
    
    return is_allowed, remaining