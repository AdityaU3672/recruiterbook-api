"""
Cache module for the application. Provides Redis caching functionality.
"""
import os
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis

# Default TTL (Time To Live) for cache entries in seconds
DEFAULT_CACHE_TTL = 3600  # 1 hour

# Redis client for direct operations
redis_client = None

async def setup_cache():
    """
    Initialize the Redis cache.
    This should be called during application startup.
    """
    global redis_client
    
    # Get Redis connection string from environment variable or use default for local development
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Create Redis connection
    redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
    redis_client = redis
    
    # Initialize FastAPI cache with Redis backend
    FastAPICache.init(
        RedisBackend(redis),
        prefix="recruiterbook-cache:",  # Prefix for all cache keys to avoid collisions
        expire=DEFAULT_CACHE_TTL,  # Default expiration time
    )

async def invalidate_cache_keys(patterns):
    """
    Invalidate cache entries matching the given patterns.
    This should be called after write operations to ensure cache consistency.
    
    Args:
        patterns (list): List of pattern strings to match cache keys.
    """
    if not redis_client:
        return
    
    for pattern in patterns:
        # Add the FastAPI Cache prefix to the pattern
        prefixed_pattern = f"recruiterbook-cache:{pattern}"
        
        # Find all keys matching the pattern
        keys = await redis_client.keys(prefixed_pattern)
        
        if keys:
            # Delete all matched keys
            await redis_client.delete(*keys)

async def invalidate_all_cache():
    """
    Invalidate all cache entries.
    This should be called for operations that affect multiple resources.
    """
    if not redis_client:
        return
        
    # Find all keys with the FastAPI Cache prefix
    keys = await redis_client.keys("recruiterbook-cache:*")
    
    if keys:
        # Delete all matched keys
        await redis_client.delete(*keys) 