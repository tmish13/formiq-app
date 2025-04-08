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

class CacheService:
    """Redis cache service for application-wide caching.
    
    This service provides a centralized interface for all Redis operations.
    It handles connection management, key expiration, and serialization.
    """
    
    def __init__(self):
        """Initialize the cache service."""
        self.redis: Optional[redis.Redis] = None
        self.available: bool = False
        self.connection_attempts: int = 0
        self.MAX_RETRIES = 3
        self.FALLBACK_CACHE: Dict[str, Any] = {}  # In-memory fallback when Redis unavailable
    
    async def connect(self) -> bool:
        """Connect to Redis server.
        
        Returns:
            bool: Connection success status
        """
        if self.redis is not None:
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
                self.redis = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            else:
                self.redis = redis.Redis(
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
        if not self.redis:
            return False
        
        try:
            result = await self.redis.ping()
            return result
        except (ConnectionError, Exception) as e:
            logger.error(f"Redis ping failed: {str(e)}")
            self.available = False
            return False
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis:
            try:
                await self.redis.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {str(e)}")
        
        self.redis = None
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
                
            result = await self.redis.get(key)
            if result is None:
                return default
                
            try:
                # Try to deserialize if it's a JSON object
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                # Return as is if not a JSON object
                return result
                
        except Exception as e:
            logger.error(f"Redis get error for key '{key}': {str(e)}")
            return self.FALLBACK_CACHE.get(key, default)
    
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
                return await self.redis.setex(key, expires_in, value)
            else:
                return await self.redis.set(key, value)
                
        except Exception as e:
            logger.error(f"Redis set error for key '{key}': {str(e)}")
            # Use in-memory fallback
            self.FALLBACK_CACHE[key] = value
            return False
    
    # Add other Redis operations as needed...

# Create singleton instance
cache_service = CacheService() 