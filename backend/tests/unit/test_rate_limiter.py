import asyncio
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.core.cache import CacheService
from app.core.exceptions import RateLimitException

@pytest.fixture(scope="function")
async def redis_client():
    """Create a Redis client for testing"""
    client = CacheService()
    await client.connect()
    await client.clear()  # Clear any existing data
    try:
        yield client
    finally:
        await client.clear()  # Clean up after tests
        await client.close()

@pytest.fixture(scope="function")
async def app(redis_client):
    """Create a test FastAPI app with rate limiter middleware"""
    app = FastAPI()
    app.add_middleware(RateLimiterMiddleware, redis_client=redis_client, requests_per_minute=5)

    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    return app

@pytest.fixture(scope="function")
def client(app):
    """Create a test client"""
    return TestClient(app)

@pytest.mark.asyncio
async def test_successful_request(client):
    """Test that a request within rate limit succeeds"""
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "success"}

@pytest.mark.asyncio
async def test_rate_limit_exceeded(client, redis_client):
    """Test that rate limit is enforced"""
    # Make requests up to the limit
    for _ in range(5):
        response = client.get("/test")
        assert response.status_code == 200

    # Next request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429

@pytest.mark.asyncio
async def test_rate_limit_per_ip(client, redis_client):
    """Test that rate limit is tracked per IP"""
    # Make requests from first IP
    for _ in range(5):
        response = client.get("/test", headers={"X-Forwarded-For": "1.1.1.1"})
        assert response.status_code == 200

    # Should be rate limited for first IP
    response = client.get("/test", headers={"X-Forwarded-For": "1.1.1.1"})
    assert response.status_code == 429

    # Should succeed for second IP
    response = client.get("/test", headers={"X-Forwarded-For": "2.2.2.2"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_rate_limit_bypass(client, redis_client):
    """Test that rate limit can be bypassed"""
    # Make requests up to the limit
    for _ in range(5):
        response = client.get("/test")
        assert response.status_code == 200

    # Should be rate limited
    response = client.get("/test")
    assert response.status_code == 429

    # Should bypass rate limit with header
    response = client.get("/test", headers={"X-Rate-Limit-Bypass": "true"})
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_docs_bypass(client, redis_client):
    """Test that documentation endpoints bypass rate limit"""
    # Make requests up to the limit
    for _ in range(5):
        response = client.get("/test")
        assert response.status_code == 200

    # Should be rate limited for normal endpoint
    response = client.get("/test")
    assert response.status_code == 429

    # Should bypass rate limit for docs
    response = client.get("/docs")
    assert response.status_code == 200
    response = client.get("/redoc")
    assert response.status_code == 200
    response = client.get("/openapi.json")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_redis_key_format(client, redis_client):
    """Test that Redis keys are formatted correctly"""
    headers = {"X-Forwarded-For": "1.1.1.1"}
    response = client.get("/test", headers=headers)
    assert response.status_code == 200

    # Check that the key exists in Redis
    key = "rate_limit:1.1.1.1"
    value = await redis_client.get(key)
    assert value == 1

@pytest.mark.asyncio
async def test_is_rate_limited_exceeded(client, redis_client):
    """Test that rate limit check works correctly"""
    key = "rate_limit:127.0.0.1"
    await redis_client.set(key, 5, expire=60)

    # Should be rate limited
    response = client.get("/test")
    assert response.status_code == 429

@pytest.mark.asyncio
async def test_check_rate_limit_exceeded(client, redis_client):
    """Test that rate limit check works correctly"""
    key = "rate_limit:127.0.0.1"
    await redis_client.set(key, 5, expire=60)

    # Should be rate limited
    response = client.get("/test")
    assert response.status_code == 429

    # Clear the rate limit
    await redis_client.clear()

    # Should succeed after clearing
    response = client.get("/test")
    assert response.status_code == 200 