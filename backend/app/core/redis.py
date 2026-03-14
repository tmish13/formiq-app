"""Redis module."""
import os
import re
from typing import Optional
from redis import Redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

redis_client: Optional[Redis] = None

_URL_MASK = re.compile(r"(redis://[^:@/]*):([^@]+)@")

def _mask_url(url: str) -> str:
    """Return Redis URL with password replaced by ***** for safe logging."""
    return _URL_MASK.sub(r"\1:*****@", url)


def get_redis() -> Redis:
    """Get Redis client instance.

    Always uses settings.REDIS_URL (set from the REDIS_URL environment
    variable on Render, or assembled from REDIS_HOST/PORT in local dev).
    Never falls back silently to localhost in production.

    Returns:
        Redis client instance
    """
    global redis_client
    if redis_client is None:
        redis_url = settings.REDIS_URL
        url_source = "REDIS_URL env var" if os.getenv("REDIS_URL") else f"assembled (REDIS_HOST={settings.REDIS_HOST})"
        logger.info(f"[Redis] Sync client connecting — source: {url_source} → {_mask_url(redis_url)}")
        try:
            redis_client = Redis.from_url(redis_url, decode_responses=True)
            # Test connection
            redis_client.ping()
            logger.info("[Redis] Sync client connected successfully")
        except Exception as e:
            logger.error(f"[Redis] Failed to connect sync client ({_mask_url(redis_url)}): {str(e)}")
            raise
    return redis_client