"""Cache service module."""
import logging
from typing import Any, Optional, List, Dict
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Service for handling Redis cache operations."""
    
    def __init__(self):
        """Initialize Redis client"""
        self.redis = None

    async def connect(self):
        """Connect to Redis"""
        try:
            if settings.ENVIRONMENT == "test":
                from tests.test_utils import MockRedis
                self.redis = MockRedis()
                logger.info("Using MockRedis for testing")
            else:
                self.redis = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    decode_responses=True
                )
                logger.info("Successfully connected to Redis")
            return self
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
            raise

    @property
    def redis_client(self):
        """Get the Redis client."""
        return self.redis

    async def ping(self) -> bool:
        """Test Redis connection."""
        return await self.redis.ping()

    async def get(self, key: str) -> Optional[int]:
        """Get value from Redis"""
        try:
            value = await self.redis.get(key)
            return int(value) if value else None
        except Exception as e:
            logger.error(f"Error getting key {key} from cache: {str(e)}")
            return None

    async def set(self, key: str, value: int, expire: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        try:
            await self.redis.set(key, str(value))
            if expire:
                await self.redis.expire(key, expire)
            return True
        except Exception as e:
            logger.error(f"Error setting key {key} in cache: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            return bool(await self.redis.delete(key))
        except Exception as e:
            logger.error(f"Error deleting key {key} from cache: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Error checking existence of key {key} in cache: {str(e)}")
            return False

    async def incr(self, key: str) -> Optional[int]:
        """Increment value in Redis"""
        try:
            return await self.redis.incr(key)
        except Exception as e:
            logger.error(f"Error incrementing key {key} in cache: {str(e)}")
            return None

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Error setting expiration for key {key} in cache: {str(e)}")
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple values from cache."""
        try:
            values = await self.redis.mget(keys)
            return dict(zip(keys, values))
        except Exception as e:
            logger.error(f"Error getting multiple keys from cache: {str(e)}")
            return {key: None for key in keys}

    async def set_many(self, key_value_pairs: Dict[str, str], expire: int = 3600) -> bool:
        """Set multiple values in cache."""
        try:
            pipeline = self.redis.pipeline()
            for key, value in key_value_pairs.items():
                await pipeline.setex(key, expire, value)
            await pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Error setting multiple keys in cache: {str(e)}")
            return False

    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple keys from cache."""
        try:
            pipeline = self.redis.pipeline()
            for key in keys:
                await pipeline.delete(key)
            await pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting multiple keys from cache: {str(e)}")
            return False

    async def clear(self) -> bool:
        """Clear all keys in Redis"""
        try:
            if self.redis:
                await self.redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False

    async def close(self):
        """Close Redis connection"""
        try:
            if self.redis:
                await self.redis.close()
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")

    async def __aenter__(self):
        """Async context manager enter"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    @classmethod
    async def create(cls):
        """Factory method to create and connect a CacheService instance"""
        self = cls()
        await self.connect()
        return self

# Create a singleton instance
cache_service = CacheService() 