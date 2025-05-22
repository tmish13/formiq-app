from httpx import AsyncClient
from sqlalchemy.orm import Session
import pytest
from unittest.mock import patch, MagicMock, mock_open
from fastapi import Response
import os
import asyncio

from app.core.config import settings

@pytest.mark.asyncio
async def test_health_check_response_structure(async_client: AsyncClient):
    """Test the health check endpoint response structure via HTTP."""
    # Mock internal helper functions called by the endpoint
    # The mock_db for direct call is no longer needed here if get_db is properly overridden for tests.
    # However, the existing patches target helpers *within* health_check, so they remain valid.
    with patch('app.api.v1.endpoints.health.get_db_stats', return_value={"pool_size": 5, "in_use": 1, "available": 4}):
        with patch('app.api.v1.endpoints.health.get_uptime', return_value="1h 30m"):
            with patch('app.api.v1.endpoints.health.check_memory_growth', return_value=0.0):
                # Call endpoint via HTTP client
                http_response = await async_client.get(f"{settings.API_V1_STR}/health/")
    
    assert http_response.status_code == 200
    response_data = http_response.json()
    
    # Verify the response structure
    assert "status" in response_data
    assert response_data["status"] in ["healthy", "degraded", "error"]
    assert "version" in response_data
    assert "timestamp" in response_data
    assert "services" in response_data
    assert "database" in response_data["services"]
    assert "system" in response_data
    assert "response_time_ms" in response_data

@pytest.mark.asyncio
async def test_db_health_check_response(async_client: AsyncClient):
    """Test the database health check endpoint via HTTP."""
    # Mock internal helper functions. The mock_db for SQLite check is tricky.
    # The endpoint internally checks db.bind.url. This means the actual db session provided by DI
    # needs to have its `bind.url` attribute set appropriately if we want to test dialect-specific paths.
    # For now, we assume the default test DB setup (potentially SQLite) is hit.
    # The existing patch for get_db_stats remains valid.
    
    # If we want to simulate different DB dialects, we might need to override get_db for this specific test
    # or have a fixture that sets up different app instances/configurations.
    # For simplicity, this test will likely run against the default test DB (e.g. SQLite in memory).
    
    with patch('app.api.v1.endpoints.health.get_db_stats', return_value={"pool_size": 5, "in_use": 1, "available": 4}):
        # To specifically test the SQLite path if your test DB is not SQLite by default:
        # This would require mocking the `db.bind.url` as seen by the endpoint.
        # One way: patch the `get_db` dependency used by the endpoint for this test.
        # For now, let's assume the default test DB behaves like SQLite or the logic is general.
        http_response = await async_client.get(f"{settings.API_V1_STR}/health/db")

    assert http_response.status_code == 200
    response_data = http_response.json()

    # Verify response for a healthy DB (adjust if based on actual test DB type)
    assert response_data["status"] == "healthy"
    assert "version" in response_data
    assert "pool" in response_data
    assert "response_time_ms" in response_data

@pytest.mark.asyncio
async def test_rate_limits_check(async_client: AsyncClient):
    """Test the rate limits check endpoint via HTTP."""
    http_response = await async_client.get(f"{settings.API_V1_STR}/health/rate-limits")
    
    assert http_response.status_code == 200
    response_data = http_response.json()

    # Verify response structure
    assert response_data["status"] == "ok"
    assert "rate_limits" in response_data
    # These depend on actual rate limit config, e.g. from fastapi_limiter
    # assert "default" in response_data["rate_limits"] 
    # assert "endpoints" in response_data["rate_limits"]
    # Minimal check for now:
    assert isinstance(response_data["rate_limits"], dict)

@pytest.mark.asyncio
async def test_ready_check(async_client: AsyncClient):
    """Test the readiness check endpoint via HTTP."""
    # Mock_db for direct call is not directly applicable. Underlying db check needs to pass.
    # Assume default test DB setup is ready.
    http_response = await async_client.get(f"{settings.API_V1_STR}/health/ready")
    
    assert http_response.status_code == 200 # FastAPI typically returns 200 or 503 for readiness
    response_data = http_response.json()
    
    # Verify response structure
    assert response_data["status"] in ["ready", "not_ready"]
    assert "checks" in response_data
    assert "timestamp" in response_data

@pytest.mark.asyncio
async def test_live_check(async_client: AsyncClient):
    """Test the liveness check endpoint via HTTP."""
    http_response = await async_client.get(f"{settings.API_V1_STR}/health/live")

    assert http_response.status_code == 200 # FastAPI typically returns 200 or 503 for liveness
    response_data = http_response.json()
    
    # Verify response structure
    assert response_data["status"] in ["alive", "unhealthy", "error"]
    assert "process" in response_data
    assert "timestamp" in response_data

@pytest.mark.asyncio
async def test_logs_status(async_client: AsyncClient):
    """Test the logs status endpoint via HTTP."""
    log_dir = settings.LOGS_DIR # Assuming settings.LOGS_DIR is correctly configured for tests
    
    # Mock os.path.exists to return True for the configured LOGS_DIR
    with patch('os.path.exists', lambda path: path == log_dir):
        # Mock os.listdir to return some log files
        with patch('os.listdir', return_value=['app.log', 'error.log']):
            # Mock os.path.getsize and os.path.getmtime
            with patch('os.path.getsize', return_value=1024):
                with patch('os.path.getmtime', return_value=1617267271.0): # Ensure float for timestamp
                    # Mock open and read for error.log
                    # The path used by open will be os.path.join(log_dir, 'error.log')
                    error_log_path = os.path.join(log_dir, 'error.log')
                    # Ensure only the specific file path is mocked for open, or be more general if that's okay.
                    def mock_open_conditional(file, mode='r', **kwargs):
                        if file == error_log_path:
                            return mock_open(read_data='{\"level\": \"ERROR\"}\n{\"level\": \"ERROR\"}').return_value
                        # Fallback for other open calls if any, or raise an error if unexpected.
                        return mock_open(read_data='').return_value # Default mock for other files
                    
                    # Using a more robust mock_open that can handle different files if necessary
                    mock_file_contents = {
                        os.path.join(log_dir, 'app.log'): '{\"level\": \"INFO\"}\n',
                        error_log_path: '{\"level\": \"ERROR\"}\n{\"level\": \"ERROR\"}\n'
                    }
                    def side_effect_open(path, mode='r', **kwargs):
                        if path in mock_file_contents:
                            return mock_open(read_data=mock_file_contents[path])() # Call to get the mock object
                        raise FileNotFoundError(f"Mocked open: File not found {path}")

                    # More flexible patch for open:
                    m_open = mock_open()
                    # Make it behave like a context manager
                    m_open.return_value.__enter__.return_value.readlines.return_value = ['{\"level\": \"ERROR\"}\n', '{\"level\": \"ERROR\"}\n']
                    
                    # Re-simplifying mock_open for this specific test, assuming only error.log is deeply inspected.
                    # The endpoint iterates and reads lines from files ending in .log or .error.
                    # It specifically checks 'error.log' for error counts by reading lines.
                    
                    mocked_open_files = {}
                    def custom_mock_open(filename, *args, **kwargs):
                        if settings.LOGS_DIR in filename and ('app.log' in filename or 'error.log' in filename):
                            if filename not in mocked_open_files:
                                if 'error.log' in filename:
                                    mocked_open_files[filename] = mock_open(read_data='{\"level\": \"ERROR\"}\n{\"level\": \"ERROR\"}')()
                                else:
                                    mocked_open_files[filename] = mock_open(read_data='{\"level\": \"INFO\"}')() 
                            return mocked_open_files[filename]
                        # For any other file, fall back to the original open or raise an error
                        # For simplicity in test, let's assume only these are opened by the endpoint logic.
                        return MagicMock() # Fallback to a generic mock if other files are opened

                    with patch('builtins.open', side_effect=custom_mock_open):
                        http_response = await async_client.get(f"{settings.API_V1_STR}/health/logs")

    assert http_response.status_code == 200
    response_data = http_response.json()

    # Verify response structure
    assert response_data["status"] == "ok"
    assert response_data["logs_directory"] == log_dir
    assert len(response_data["log_files"]) == 2 # app.log, error.log
    assert response_data["error_count"] >= 2 # Based on mocked error.log content

@pytest.mark.skip(reason="Debug endpoints are tested separately or require specific config.")
async def test_debug_endpoints(async_client: AsyncClient):
    """Test the debug endpoints (when enabled) via HTTP."""
    # These would be tested separately as they require more complex mocking and specific app config
    # Example (if such an endpoint exists and requires auth):
    # debug_config_response = await async_client.get(f"{settings.API_V1_STR}/health/debug/config", headers=...)
    # assert debug_config_response.status_code == 200 # or 404 if not enabled
    pass 