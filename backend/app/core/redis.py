"""Redis client configuration."""
from redis import Redis
from app.core.config import settings
from app.core.logging import logger

def get_redis_client() -> Redis:
    """Get Redis client instance."""
    try:
        client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        # Test connection
        client.ping()
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise 