"""Test utilities module."""
from typing import Dict, Any, List

class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.data = {}
        
    async def get(self, key: str):
        return self.data.get(key)
        
    async def set(self, key: str, value: str):
        self.data[key] = value
        return True
        
    async def expire(self, key: str, seconds: int):
        return True
        
    async def incr(self, key: str):
        if key not in self.data:
            self.data[key] = "0"
        self.data[key] = str(int(self.data[key]) + 1)
        return int(self.data[key])
        
    async def flushdb(self):
        self.data = {}
        return True
        
    async def close(self):
        pass
        
    async def ping(self):
        return True
        
    def keys(self, pattern):
        return [k for k in self.data.keys() if k.startswith(pattern)]
        
    def exists(self, key):
        return key in self.data
        
    def mget(self, keys):
        return [self.data.get(k) for k in keys]
        
    def pipeline(self):
        return self

    def execute(self):
        return True

    def ttl(self, key):
        return 3600

    def info(self):
        return {
            "used_memory": 0,
            "connected_clients": 1,
            "total_connections_received": 0,
            "total_commands_processed": 0,
            "instantaneous_ops_per_sec": 0,
            "hit_rate": 1.0
        } 