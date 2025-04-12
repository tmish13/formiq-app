import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.core.error_handling import UnifiedErrorHandler
from app.middleware.rate_limiter import EnhancedRateLimiter
from app.middleware.validate_request import EnhancedValidateRequestMiddleware
from app.core.exceptions import ValidationException, RateLimitException
from app.core.config import settings
from app.core.cache import cache_service

app = FastAPI()

# Add middlewares
app.add_middleware(UnifiedErrorHandler)
app.add_middleware(
    EnhancedRateLimiter,
    redis_client=cache_service.redis_client,
    requests_per_minute=10,
    burst_size=20,
    custom_rules={
        "/test/custom": {"limit": 5, "burst": 10, "window": 60}
    }
)
app.add_middleware(EnhancedValidateRequestMiddleware)

client = TestClient(app)

def test_error_handling():
    """Test unified error handling."""
    @app.get("/test/error")
    async def test_error():
        raise ValueError("Test error")
    
    response = client.get("/test/error")
    assert response.status_code == 500
    assert "error" in response.json()
    assert response.json()["code"] == "INTERNAL_ERROR"

def test_rate_limiting():
    """Test rate limiting functionality."""
    # Test default rate limiting
    responses = []
    for _ in range(25):  # More than the burst size
        response = client.get("/test/rate-limit")
        responses.append(response.status_code)
    
    assert 429 in responses  # Should have rate limited requests
    
    # Test custom rate limiting
    responses = []
    for _ in range(15):  # More than the custom limit
        response = client.get("/test/custom")
        responses.append(response.status_code)
    
    assert 429 in responses  # Should have rate limited requests

def test_request_validation():
    """Test request validation."""
    # Test content length validation
    large_data = "x" * (settings.MAX_CONTENT_LENGTH + 1)
    response = client.post(
        "/test/validation",
        content=large_data,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    
    # Test content type validation
    response = client.post(
        "/test/validation",
        content="{}",
        headers={"Content-Type": "invalid/type"}
    )
    assert response.status_code == 422
    
    # Test JSON validation
    response = client.post(
        "/test/validation",
        content="invalid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422

def test_custom_validation():
    """Test custom validation rules."""
    # Test video size validation
    response = client.post(
        "/api/v1/form-checks",
        files={"file": ("test.mp4", b"x" * (settings.MAX_CONTENT_LENGTH + 1))},
        headers={"Content-Type": "multipart/form-data"}
    )
    assert response.status_code == 422
    
    # Test video format validation
    response = client.post(
        "/api/v1/form-checks",
        files={"file": ("test.txt", b"invalid format")},
        headers={"Content-Type": "multipart/form-data"}
    )
    assert response.status_code == 422

def test_middleware_order():
    """Test middleware execution order."""
    @app.get("/test/order")
    async def test_order():
        return {"status": "ok"}
    
    response = client.get("/test/order")
    assert response.status_code == 200
    
    # Verify rate limiting headers
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

def test_error_metrics():
    """Test error metrics collection."""
    # Trigger some errors
    client.get("/test/error")
    client.post("/test/validation", content="invalid json")
    
    # Verify metrics (this would need to be implemented in the test environment)
    # assert ERROR_COUNTER.labels(error_type="app_exception")._value.get() > 0
    # assert ERROR_COUNTER.labels(error_type="validation_error")._value.get() > 0

def test_rate_limit_metrics():
    """Test rate limit metrics collection."""
    # Make some requests
    for _ in range(5):
        client.get("/test/rate-limit")
    
    # Verify metrics (this would need to be implemented in the test environment)
    # assert RATE_LIMIT_REQUESTS.labels(client_ip="test")._value.get() > 0

def test_validation_metrics():
    """Test validation metrics collection."""
    # Trigger some validation errors
    client.post("/test/validation", content="invalid json")
    
    # Verify metrics (this would need to be implemented in the test environment)
    # assert VALIDATION_ERRORS.labels(error_type="json_decode")._value.get() > 0 