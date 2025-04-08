from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pytest
from unittest.mock import patch, MagicMock, mock_open
from fastapi import Response
import os
import asyncio

from app.api.v1.endpoints.health import router, health_check, db_health_check, rate_limit_status, readiness_check, liveness_check, logs_status

@pytest.mark.asyncio
async def test_health_check_response_structure():
    """Test the health check endpoint response structure."""
    # Mock the database session
    mock_db = MagicMock()
    mock_db.execute().scalar.return_value = 1
    
    # Call the endpoint function directly
    with patch('app.api.v1.endpoints.health.get_db_stats', return_value={"pool_size": 5, "in_use": 1, "available": 4}):
        with patch('app.api.v1.endpoints.health.get_uptime', return_value="1h 30m"):
            with patch('app.api.v1.endpoints.health.check_memory_growth', return_value=0.0):
                response = await health_check(db=mock_db)
    
    # Verify the response structure
    assert "status" in response
    assert response["status"] in ["healthy", "degraded"]
    assert "version" in response
    assert "timestamp" in response
    assert "services" in response
    assert "database" in response["services"]
    assert "system" in response
    assert "response_time_ms" in response

@pytest.mark.asyncio
async def test_db_health_check_response():
    """Test the database health check endpoint."""
    # Mock the database session for SQLite connection
    mock_db = MagicMock()
    # Set up mock to indicate this is SQLite
    mock_db.bind.url = "sqlite:///test.db"
    
    # Call the endpoint function directly
    with patch('app.api.v1.endpoints.health.get_db_stats', return_value={"pool_size": 5, "in_use": 1, "available": 4}):
        response = await db_health_check(db=mock_db)
    
    # Verify SQLite response
    assert response["status"] == "healthy"
    assert "version" in response
    assert "pool" in response
    assert "response_time_ms" in response

@pytest.mark.asyncio
async def test_rate_limits_check():
    """Test the rate limits check endpoint."""
    # Call the endpoint function directly
    response = await rate_limit_status()
    
    # Verify response structure
    assert response["status"] == "ok"
    assert "rate_limits" in response
    assert "default" in response["rate_limits"]
    assert "endpoints" in response["rate_limits"]

@pytest.mark.asyncio
async def test_ready_check():
    """Test the readiness check endpoint."""
    # Mock the database session
    mock_db = MagicMock()
    mock_db.execute().scalar.return_value = 1
    
    # Call the endpoint function directly
    response = await readiness_check(db=mock_db)
    
    # Verify response structure
    assert response["status"] in ["ready", "not_ready"]
    assert "checks" in response
    assert "timestamp" in response

@pytest.mark.asyncio
async def test_live_check():
    """Test the liveness check endpoint."""
    # Call the endpoint function directly
    response = await liveness_check()
    
    # Verify response structure
    assert response["status"] in ["alive", "unhealthy", "error"]
    assert "process" in response
    assert "timestamp" in response

@pytest.mark.asyncio
async def test_logs_status():
    """Test the logs status endpoint."""
    # Mock os.path.exists to return True
    with patch('os.path.exists', return_value=True):
        # Mock os.listdir to return some log files
        with patch('os.listdir', return_value=['app.log', 'error.log']):
            # Mock os.path.getsize and os.path.getmtime
            with patch('os.path.getsize', return_value=1024):
                with patch('os.path.getmtime', return_value=1617267271):
                    # Mock open and read for error.log
                    m = mock_open(read_data='"level": "ERROR"\n"level": "ERROR"')
                    with patch('builtins.open', m):
                        # Call the endpoint function directly
                        response = await logs_status()
    
    # Verify response structure
    assert response["status"] == "ok"
    assert "logs_directory" in response
    assert "log_files" in response
    assert "error_count" in response

@pytest.mark.skip(reason="Debug endpoints are tested separately")
def test_debug_endpoints():
    """Test the debug endpoints (when enabled)."""
    # These would be tested separately as they require more complex mocking
    pass 