import json
from typing import Any, Optional, List
import redis
from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import AppException

class CacheService:
    """Redis cache service with proper error handling and logging."""
    
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info("redis_connection_successful")
        except redis.ConnectionError as e:
            logger.error("redis_connection_failed", error=str(e))
            raise AppException("Redis connection failed", "CACHE_ERROR")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except redis.RedisError as e:
            logger.error("redis_get_error", key=key, error=str(e))
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration."""
        try:
            return self.redis_client.setex(
                key,
                expire,
                json.dumps(value)
            )
        except redis.RedisError as e:
            logger.error("redis_set_error", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            return bool(self.redis_client.delete(key))
        except redis.RedisError as e:
            logger.error("redis_delete_error", key=key, error=str(e))
            return False
    
    def delete_pattern(self, pattern: str) -> bool:
        """Delete all keys matching pattern."""
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return bool(self.redis_client.delete(*keys))
            return True
        except redis.RedisError as e:
            logger.error("redis_delete_pattern_error", pattern=pattern, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.redis_client.exists(key))
        except redis.RedisError as e:
            logger.error("redis_exists_error", key=key, error=str(e))
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment value in cache."""
        try:
            return self.redis_client.incr(key, amount)
        except redis.RedisError as e:
            logger.error("redis_increment_error", key=key, error=str(e))
            return None
    
    def get_many(self, keys: List[str]) -> List[Optional[Any]]:
        """Get multiple values from cache."""
        try:
            values = self.redis_client.mget(keys)
            return [json.loads(v) if v else None for v in values]
        except redis.RedisError as e:
            logger.error("redis_get_many_error", keys=keys, error=str(e))
            return [None] * len(keys)
    
    def set_many(self, mapping: dict, expire: int = 3600) -> bool:
        """Set multiple values in cache."""
        try:
            pipe = self.redis_client.pipeline()
            for key, value in mapping.items():
                pipe.setex(key, expire, json.dumps(value))
            pipe.execute()
            return True
        except redis.RedisError as e:
            logger.error("redis_set_many_error", error=str(e))
            return False

# Create singleton instance
cache_service = CacheService() 