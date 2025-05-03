"""Redis cache service module."""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set, Union

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Redis connection pool
_redis_pool: Optional[redis.Redis] = None

async def init_redis_pool() -> None:
    """Initialize Redis connection pool."""
    global _redis_pool
    try:
        if not _redis_pool:
            _redis_pool = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Redis connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Redis pool: {e}")
        raise

async def get_redis() -> redis.Redis:
    """Get Redis connection from pool."""
    if not _redis_pool:
        await init_redis_pool()
    return _redis_pool

async def close_redis_pool() -> None:
    """Close Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis connection pool closed")

async def set_cache(key: str, value: Any, expire: int = 3600) -> None:
    """Set value in cache with expiration."""
    redis = await get_redis()
    await redis.set(key, value, ex=expire)

async def get_cache(key: str) -> Optional[str]:
    """Get value from cache."""
    redis = await get_redis()
    return await redis.get(key)

async def delete_cache(key: str) -> None:
    """Delete value from cache."""
    redis = await get_redis()
    await redis.delete(key)

async def increment_counter(key: str, expire: int = 3600) -> int:
    """Increment counter and return new value."""
    redis = await get_redis()
    value = await redis.incr(key)
    if expire:
        await redis.expire(key, expire)
    return value

async def get_counter(key: str) -> int:
    """Get counter value."""
    redis = await get_redis()
    value = await redis.get(key)
    return int(value) if value else 0

class CacheService:
    """Redis cache service for application-wide caching.
    
    This service provides a centralized interface for all Redis operations.
    It handles connection management, key expiration, and serialization.
    """
    
    def __init__(self):
        """Initialize the cache service."""
        self._redis: Optional[redis.Redis] = None
        self.available: bool = False
        self.connection_attempts: int = 0
        self.MAX_RETRIES = 3
        self.FALLBACK_CACHE: Dict[str, Any] = {}  # In-memory fallback when Redis unavailable
    
    @property
    def redis_client(self) -> Optional[redis.Redis]:
        """Get the Redis client instance."""
        return self._redis
    
    async def connect(self) -> bool:
        """Connect to Redis server.
        
        Returns:
            bool: Connection success status
        """
        if self._redis is not None:
            # Already connected
            return self.available
        
        if not settings.REDIS_URL and not (settings.REDIS_HOST and settings.REDIS_PORT):
            logger.warning("Redis configuration not found. Caching disabled.")
            self.available = False
            return False
        
        try:
            self.connection_attempts += 1
            
            # Connect to Redis
            if settings.REDIS_URL:
                self._redis = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            else:
                self._redis = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    encoding="utf-8",
                    decode_responses=True
                )
            
            # Test connection
            await self.ping()
            self.available = True
            logger.info("Connected to Redis server")
            return True
            
        except (ConnectionError, Exception) as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.available = False
            
            # In production, retry connection
            if settings.ENVIRONMENT == "production" and self.connection_attempts <= self.MAX_RETRIES:
                retry_delay = 2 ** self.connection_attempts  # Exponential backoff
                logger.info(f"Retrying Redis connection in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                return await self.connect()
                
            # Fallback to in-memory cache in development/test
            if settings.ENVIRONMENT in ["development", "test"]:
                logger.warning("Using in-memory cache as Redis fallback")
            
            return False
    
    async def ping(self) -> bool:
        """Test Redis connection.
        
        Returns:
            bool: Connection status
        """
        if not self._redis:
            return False
        
        try:
            result = await self._redis.ping()
            return result
        except (ConnectionError, Exception) as e:
            logger.error(f"Redis ping failed: {str(e)}")
            self.available = False
            return False
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            try:
                await self._redis.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {str(e)}")
        
        self._redis = None
        self.available = False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Any: Retrieved value or default
        """
        try:
            if not self.available:
                return self.FALLBACK_CACHE.get(key, default)
                
            result = await self._redis.get(key)
            if result is None:
                return default
                
            try:
                # Try to deserialize if it's a JSON object
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                # Return as is if not a JSON object
                return result
                
        except Exception as e:
            logger.error(f"Error getting value from cache: {str(e)}")
            return default
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expires_in: Optional[int] = None
    ) -> bool:
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to store
            expires_in: Expiration time in seconds
            
        Returns:
            bool: Success status
        """
        try:
            if not self.available:
                self.FALLBACK_CACHE[key] = value
                return True
                
            # Serialize complex objects
            if not isinstance(value, (str, int, float, bool)) and value is not None:
                value = json.dumps(value)
                
            if expires_in:
                return await self._redis.setex(key, expires_in, value)
            else:
                return await self._redis.set(key, value)
                
        except Exception as e:
            logger.error(f"Redis set error for key '{key}': {str(e)}")
            # Use in-memory fallback
            self.FALLBACK_CACHE[key] = value
            return False
    
    # Add other Redis operations as needed...

async def init_cache():
    """Initialize the cache service at application startup."""
    logger.info("Initializing cache service")
    try:
        await cache_service.connect()
        if cache_service.available:
            # Clear any stale data from previous runs in development/test
            if settings.ENVIRONMENT in ["development", "test"]:
                logger.info("Development/test environment - clearing cache")
                # We don't want to completely flush in case Redis is shared
                # Instead, clear application-specific keys
                if cache_service.redis_client:
                    keys = await cache_service.redis_client.keys(f"{settings.PROJECT_NAME.lower()}:*")
                    if keys:
                        await cache_service.redis_client.delete(*keys)
                        logger.info(f"Cleared {len(keys)} cached items")
            
            logger.info("Cache service initialized successfully")
        else:
            logger.warning("Redis unavailable - using memory cache fallback")
    except Exception as e:
        logger.error(f"Failed to initialize cache service: {str(e)}")
        # Do not raise error to prevent application startup failure
        # Application can still function without cache

# Initialize global cache service instance
cache_service = CacheService()

# Alias for backward compatibility
redis_cache = cache_service 