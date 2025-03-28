from redis import Redis, ConnectionPool, RedisError
from app.core.config import settings
from app.core.logger import logger
from functools import lru_cache
import time
from typing import Optional

class RedisConnectionError(Exception):
    """Custom exception for Redis connection errors."""
    pass

@lru_cache()
def get_redis_pool() -> ConnectionPool:
    """Get Redis connection pool with retries."""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test pool connection
            test_client = Redis(connection_pool=pool)
            test_client.ping()
            test_client.close()
            logger.info("redis_pool_created_successfully")
            return pool
        except RedisError as e:
            if attempt == max_retries - 1:
                logger.error(
                    "redis_pool_creation_failed",
                    error=str(e),
                    attempts=attempt + 1
                )
                raise RedisConnectionError(f"Failed to create Redis pool after {max_retries} attempts")
            logger.warning(
                "redis_pool_creation_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e)
            )
            time.sleep(retry_delay)

@lru_cache()
def get_redis_client() -> Redis:
    """Get Redis client with connection pool and health check."""
    try:
        pool = get_redis_pool()
        client = Redis(connection_pool=pool)
        # Test connection
        client.ping()
        logger.info("redis_client_initialized")
        return client
    except RedisError as e:
        logger.error("redis_client_initialization_failed", error=str(e))
        raise RedisConnectionError("Failed to initialize Redis client")

def check_redis_connection() -> bool:
    """Check if Redis connection is working with retries."""
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            client = get_redis_client()
            client.ping()
            return True
        except RedisError as e:
            if attempt == max_retries - 1:
                logger.error(
                    "redis_connection_check_failed",
                    error=str(e),
                    attempts=attempt + 1
                )
                return False
            logger.warning(
                "redis_connection_check_retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e)
            )
            time.sleep(retry_delay)
    
    return False 