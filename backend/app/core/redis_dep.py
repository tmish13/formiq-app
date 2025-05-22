import redis
from app.core.redis import get_redis as get_sync_redis_client

def get_redis_client() -> redis.Redis:
    return get_sync_redis_client() 