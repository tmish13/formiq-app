"""Redis client factory module."""
from typing import Optional
from redis import Redis, ConnectionPool
from app.core.config import settings
from app.core.logging import logger

_redis_pool: Optional[ConnectionPool] = None

def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=False  # Keep as bytes for security-sensitive data
        )
    return _redis_pool

def get_redis_client() -> Redis:
    """Get Redis client instance."""
    try:
        pool = get_redis_pool()
        client = Redis(connection_pool=pool)
        # Test connection
        client.ping()
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise 