"""Cache service module."""
import logging
import json
from typing import Any, Optional, List, Dict, Union
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Service for handling Redis cache operations."""
    
    def __init__(self):
        """Initialize Redis client"""
        self.redis = None
        self._available = False
        self.default_ttl = 3600  # 1 hour default TTL

    async def connect(self):
        """Connect to Redis"""
        if settings.ENVIRONMENT == "test":
            try:
                from tests.test_utils import MockRedis
                self.redis = MockRedis()
                self._available = True
                logger.info("Using MockRedis for testing")
            except ImportError:
                logger.warning("MockRedis not available for testing")
                self._available = False
            return self
            
        # Production/development environment
        try:
            if not settings.REDIS_HOST or not settings.REDIS_PORT:
                logger.warning("Redis configuration is incomplete, skipping connection")
                self._available = False
                return self
            
            # Create connection pool for better performance with many users
            redis_url = settings.REDIS_URL or f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            
            # Configure more connection options for larger scale
            self.redis = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,        # 5 second socket timeout
                socket_connect_timeout=3,  # 3 second connect timeout
                health_check_interval=30,  # Check connection every 30 seconds
                max_connections=50,        # Up to 50 connections in the pool
                retry_on_timeout=True      # Retry operations on timeout
            )
            
            # Test connection
            await self.redis.ping()
            self._available = True
            
            # Set default TTL from config if available
            if hasattr(settings, 'CACHE_TTL') and settings.CACHE_TTL:
                self.default_ttl = settings.CACHE_TTL
                
            logger.info(f"Successfully connected to Redis at {redis_url}")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
            self._available = False
            self.redis = None
            # Only raise in production environment
            if settings.ENVIRONMENT == "production":
                raise
        return self

    @property
    def redis_client(self):
        """Get the Redis client."""
        return self.redis

    @property
    def available(self) -> bool:
        """Check if Redis is available."""
        return self._available and self.redis is not None

    async def ping(self) -> bool:
        """Test Redis connection."""
        if not self.available:
            return False
        try:
            return await self.redis.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {str(e)}")
            self._available = False
            return False

    async def get(self, key: str) -> Any:
        """Get value from Redis"""
        if not self.available:
            return None
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
                
            # Try to parse JSON, but return raw string if not JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Error getting key {key} from cache: {str(e)}")
            return None

    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        if not self.available:
            return False
        try:
            # Convert dict/list to JSON string
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, (str, int, float, bool)):
                value = str(value)
                
            # Use default TTL if not specified
            if expire is None:
                expire = self.default_ttl
                
            await self.redis.setex(key, expire, value)
            return True
        except Exception as e:
            logger.error(f"Error setting key {key} in cache: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.available:
            return False
        try:
            return bool(await self.redis.delete(key))
        except Exception as e:
            logger.error(f"Error deleting key {key} from cache: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.available:
            return False
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Error checking existence of key {key} in cache: {str(e)}")
            return False

    async def incr(self, key: str) -> Optional[int]:
        """Increment value in Redis"""
        if not self.available:
            return None
        try:
            return await self.redis.incr(key)
        except Exception as e:
            logger.error(f"Error incrementing key {key} in cache: {str(e)}")
            return None

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        if not self.available:
            return False
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Error setting expiration for key {key} in cache: {str(e)}")
            return False

    async def ttl(self, key: str) -> int:
        """Get time to live for a key in seconds."""
        if not self.available:
            return -2  # -2 means key doesn't exist (Redis convention)
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {str(e)}")
            return -2

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[Any]]:
        """Get multiple values from cache."""
        if not self.available:
            return {key: None for key in keys}
        try:
            values = await self.redis.mget(keys)
            result = {}
            
            for i, key in enumerate(keys):
                value = values[i]
                if value is None:
                    result[key] = None
                    continue
                    
                # Try to parse JSON
                try:
                    result[key] = json.loads(value)
                except json.JSONDecodeError:
                    result[key] = value
                    
            return result
        except Exception as e:
            logger.error(f"Error getting multiple keys from cache: {str(e)}")
            return {key: None for key in keys}

    async def set_many(self, key_value_pairs: Dict[str, Any], expire: int = None) -> bool:
        """Set multiple values in cache."""
        if not self.available:
            return False
            
        # Use default TTL if not specified
        if expire is None:
            expire = self.default_ttl
            
        try:
            pipeline = self.redis.pipeline()
            for key, value in key_value_pairs.items():
                # Convert dict/list to JSON string
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                elif not isinstance(value, (str, int, float, bool)):
                    value = str(value)
                    
                await pipeline.setex(key, expire, value)
            await pipeline.execute()
            return True
        except Exception as e:
            logger.error(f"Error setting multiple keys in cache: {str(e)}")
            return False

    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple keys from cache."""
        if not self.available:
            return False
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
        if not self.available:
            return False
        try:
            await self.redis.flushdb()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self.available and self.redis:
            try:
                await self.redis.close()
                self._available = False
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
        
    # Application-specific cache methods for FormIQ
    
    async def cache_form_check(self, form_check_id: str, data: Dict[str, Any], ttl: int = None) -> bool:
        """Cache form check data."""
        key = f"form_check:{form_check_id}"
        return await self.set(key, data, ttl)
        
    async def get_form_check(self, form_check_id: str) -> Optional[Dict[str, Any]]:
        """Get cached form check data."""
        key = f"form_check:{form_check_id}"
        return await self.get(key)
        
    async def invalidate_form_check(self, form_check_id: str) -> bool:
        """Invalidate form check cache."""
        key = f"form_check:{form_check_id}"
        return await self.delete(key)
        
    async def cache_user_form_checks(self, user_id: str, form_checks: List[Dict[str, Any]], ttl: int = None) -> bool:
        """Cache user's form checks."""
        key = f"user:{user_id}:form_checks"
        return await self.set(key, form_checks, ttl)
        
    async def get_user_form_checks(self, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached user's form checks."""
        key = f"user:{user_id}:form_checks"
        return await self.get(key)
        
    async def cache_exercise(self, exercise_id: str, data: Dict[str, Any], ttl: int = None) -> bool:
        """Cache exercise data."""
        key = f"exercise:{exercise_id}"
        return await self.set(key, data, ttl)
        
    async def get_exercise(self, exercise_id: str) -> Optional[Dict[str, Any]]:
        """Get cached exercise data."""
        key = f"exercise:{exercise_id}"
        return await self.get(key)
        
    async def cache_all_exercises(self, exercises: List[Dict[str, Any]], ttl: int = None) -> bool:
        """Cache all exercises."""
        key = "exercises:all"
        return await self.set(key, exercises, ttl)
        
    async def get_all_exercises(self) -> Optional[List[Dict[str, Any]]]:
        """Get all cached exercises."""
        key = "exercises:all"
        return await self.get(key)

# Create a singleton instance
cache_service = CacheService() 