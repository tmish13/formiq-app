import pytest
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
import redis.asyncio as redis
from app.middleware.rate_limiter import RateLimiter
from app.core.config import settings
from app.models.user import User
from app.core.security import create_access_token
from app.core.logging import logger
from unittest.mock import Mock, patch

# Create a test FastAPI app
app = FastAPI()

# Initialize Redis client for testing
redis_client = redis.Redis.from_url(settings.REDIS_URL)

# Add rate limiter middleware
app.add_middleware(RateLimiter, redis_client=redis_client)

# Test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "success"}

# Test client
client = TestClient(app)

@pytest.fixture(autouse=True)
async def clear_redis():
    """Clear Redis before and after each test"""
    await redis_client.flushall()
    yield
    await redis_client.flushall()

def test_successful_request():
    """Test that a single request is successful"""
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "success"}

def test_rate_limit_exceeded():
    """Test that requests are rate limited after exceeding the limit"""
    # Make requests up to the limit
    for _ in range(60):  # Default limit is 60 requests per minute
        response = client.get("/test")
        assert response.status_code == 200

    # The next request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]

def test_rate_limit_per_ip():
    """Test that rate limits are applied per IP address"""
    # Make requests from first IP
    headers_1 = {"X-Forwarded-For": "1.1.1.1"}
    for _ in range(60):
        response = client.get("/test", headers=headers_1)
        assert response.status_code == 200

    # Next request from first IP should be rate limited
    response = client.get("/test", headers=headers_1)
    assert response.status_code == 429

    # Requests from second IP should still work
    headers_2 = {"X-Forwarded-For": "2.2.2.2"}
    response = client.get("/test", headers=headers_2)
    assert response.status_code == 200

def test_rate_limit_reset():
    """Test that rate limits are reset after the window period"""
    # Make some requests
    for _ in range(30):
        response = client.get("/test")
        assert response.status_code == 200

    # Wait for the rate limit window to reset (in test environment, we'll use a shorter window)
    asyncio.run(asyncio.sleep(1))

    # Should be able to make more requests
    response = client.get("/test")
    assert response.status_code == 200

def test_missing_redis_connection():
    """Test behavior when Redis connection fails"""
    # Create a new app with a non-existent Redis connection
    test_app = FastAPI()
    bad_redis = redis.Redis.from_url("redis://nonexistent:6379")
    test_app.add_middleware(RateLimiter, redis_client=bad_redis)

    @test_app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    test_client = TestClient(test_app)

    # Request should still succeed (fail open)
    response = test_client.get("/test")
    assert response.status_code == 200

def test_rate_limit_headers():
    """Test that rate limit headers are included in the response"""
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

def test_burst_requests():
    """Test handling of burst requests"""
    # Send multiple requests concurrently
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(client.get, "/test") for _ in range(20)]
        responses = [future.result() for future in futures]

    # All requests should have either succeeded or been rate limited
    for response in responses:
        assert response.status_code in [200, 429]

def test_custom_rate_limit():
    """Test custom rate limit for specific endpoint"""
    # Create a new app with custom rate limits
    test_app = FastAPI()
    test_app.add_middleware(
        RateLimiter,
        redis_client=redis_client,
        rate_limit=10,  # Lower rate limit for testing
        window_seconds=60
    )

    @test_app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    test_client = TestClient(test_app)

    # Make requests up to the custom limit
    for _ in range(10):
        response = test_client.get("/test")
        assert response.status_code == 200

    # Next request should be rate limited
    response = test_client.get("/test")
    assert response.status_code == 429

def test_rate_limit_bypass():
    """Test that rate limit can be bypassed with special header"""
    # Make requests up to the limit
    for _ in range(60):
        response = client.get("/test")
        assert response.status_code == 200

    # Normal request should be rate limited
    response = client.get("/test")
    assert response.status_code == 429

    # Request with bypass header should succeed
    response = client.get("/test", headers={"X-RateLimit-Bypass": settings.rate_limit_bypass_key})
    assert response.status_code == 200

def test_malformed_ip():
    """Test handling of malformed IP addresses"""
    headers = {"X-Forwarded-For": "invalid-ip"}
    response = client.get("/test", headers=headers)
    assert response.status_code == 200  # Should use default IP handling

def test_redis_key_format():
    """Test that Redis keys are properly formatted"""
    response = client.get("/test", headers={"X-Forwarded-For": "1.1.1.1"})
    assert response.status_code == 200

    # Check that the Redis key exists and is properly formatted
    key = f"rate_limit:1.1.1.1"
    assert asyncio.run(redis_client.exists(key)) == 1

@pytest.fixture
def rate_limiter():
    return RateLimiter(requests_per_minute=60)

@pytest.fixture
def mock_request():
    request = Mock()
    request.client.host = "127.0.0.1"
    return request

@pytest.fixture
def redis_client():
    redis_client = redis.Redis.from_url(settings.REDIS_URL)
    yield redis_client
    redis_client.close()

def test_rate_limiter_init(rate_limiter):
    assert rate_limiter.requests_per_minute == 60
    assert isinstance(rate_limiter.requests, dict)

def test_is_rate_limited_not_exceeded(rate_limiter, mock_request):
    assert not rate_limiter.is_rate_limited(mock_request.client.host)

def test_is_rate_limited_exceeded(rate_limiter, mock_request):
    # Simulate multiple requests
    for _ in range(60):
        rate_limiter.is_rate_limited(mock_request.client.host)
    
    # Next request should be rate limited
    assert rate_limiter.is_rate_limited(mock_request.client.host)

@pytest.mark.asyncio
async def test_check_rate_limit_not_exceeded(rate_limiter, mock_request):
    # Should not raise an exception
    await rate_limiter.check_rate_limit(mock_request)

@pytest.mark.asyncio
async def test_check_rate_limit_exceeded(rate_limiter, mock_request):
    # Simulate multiple requests
    for _ in range(60):
        rate_limiter.is_rate_limited(mock_request.client.host)
    
    # Next request should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await rate_limiter.check_rate_limit(mock_request)
    
    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "Too many requests" 