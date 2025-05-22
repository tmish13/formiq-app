"""Redis module."""
from typing import Optional
from redis import Redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

redis_client: Optional[Redis] = None

def get_redis() -> Redis:
    """Get Redis client instance.
    
    Returns:
        Redis client instance
    """
    global redis_client
    if redis_client is None:
        try:
            redis_client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            # Test connection
            redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    return redis_client 