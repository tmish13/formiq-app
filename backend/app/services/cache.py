from typing import Any, Optional, Union
from redis import Redis, RedisError
from app.core.redis import get_redis_client
from app.core.logger import logger
import json
from datetime import timedelta

class CacheService:
    """Service for handling Redis caching operations."""
    
    def __init__(self):
        self.redis = get_redis_client()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = self.redis.get(key)
            return json.loads(value) if value else None
        except RedisError as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """Set value in cache with optional expiration."""
        try:
            serialized = json.dumps(value)
            if expire:
                return self.redis.setex(key, expire, serialized)
            return self.redis.set(key, serialized)
        except RedisError as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            return bool(self.redis.delete(key))
        except RedisError as e:
            logger.error("cache_delete_error", key=key, error=str(e))
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            return bool(self.redis.exists(key))
        except RedisError as e:
            logger.error("cache_exists_error", key=key, error=str(e))
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment value in cache."""
        try:
            return self.redis.incr(key, amount)
        except RedisError as e:
            logger.error("cache_increment_error", key=key, error=str(e))
            return None
    
    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement value in cache."""
        try:
            return self.redis.decr(key, amount)
        except RedisError as e:
            logger.error("cache_decrement_error", key=key, error=str(e))
            return None
    
    def get_or_set(
        self,
        key: str,
        default: Any,
        expire: Optional[Union[int, timedelta]] = None
    ) -> Any:
        """Get value from cache or set default if not exists."""
        value = self.get(key)
        if value is None:
            self.set(key, default, expire)
            return default
        return value

# Create singleton instance
cache_service = CacheService() 