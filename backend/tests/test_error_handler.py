import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from ..middleware.error_handler import ErrorHandler
import logging

# Create a test FastAPI app
app = FastAPI()

# Add error handler middleware
app.add_middleware(ErrorHandler)

# Test endpoints
@app.get("/test-success")
async def test_success():
    return {"message": "success"}

@app.get("/test-http-error")
async def test_http_error():
    raise HTTPException(status_code=400, detail="Bad request")

@app.get("/test-validation-error")
async def test_validation_error():
    # Simulate a validation error
    raise ValueError("Invalid input")

@app.get("/test-database-error")
async def test_database_error():
    # Simulate a database error
    raise Exception("Database connection failed")

@app.get("/test-custom-error")
async def test_custom_error():
    class CustomError(Exception):
        def __init__(self, message: str):
            self.message = message
            super().__init__(self.message)

    raise CustomError("Custom error occurred")

# Test client
client = TestClient(app)

def test_successful_request(caplog):
    """Test that successful requests are handled normally"""
    with caplog.at_level(logging.INFO):
        response = client.get("/test-success")
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
        
        # Check that the request was logged
        assert any(
            record.levelname == "INFO" and "Request completed" in record.message
            for record in caplog.records
        )

def test_http_exception(caplog):
    """Test handling of HTTPException"""
    with caplog.at_level(logging.WARNING):
        response = client.get("/test-http-error")
        assert response.status_code == 400
        assert response.json() == {
            "detail": "Bad request",
            "status_code": 400,
            "type": "HTTPException"
        }
        
        # Check that the error was logged
        assert any(
            record.levelname == "WARNING" and "HTTP error occurred" in record.message
            for record in caplog.records
        )

def test_validation_error(caplog):
    """Test handling of validation errors"""
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-validation-error")
        assert response.status_code == 500
        error_response = response.json()
        assert error_response["type"] == "ValueError"
        assert error_response["detail"] == "Invalid input"
        assert "timestamp" in error_response
        assert "request_id" in error_response
        
        # Check that the error was logged
        assert any(
            record.levelname == "ERROR" and "Unhandled error occurred" in record.message
            for record in caplog.records
        )

def test_database_error(caplog):
    """Test handling of database errors"""
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-database-error")
        assert response.status_code == 500
        error_response = response.json()
        assert error_response["type"] == "Exception"
        assert error_response["detail"] == "Database connection failed"
        assert "timestamp" in error_response
        assert "request_id" in error_response
        
        # Check that the error was logged with stack trace
        assert any(
            record.levelname == "ERROR" and "Database connection failed" in record.message
            for record in caplog.records
        )

def test_custom_error(caplog):
    """Test handling of custom error types"""
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-custom-error")
        assert response.status_code == 500
        error_response = response.json()
        assert error_response["type"] == "CustomError"
        assert error_response["detail"] == "Custom error occurred"
        assert "timestamp" in error_response
        assert "request_id" in error_response
        
        # Check that the error was logged
        assert any(
            record.levelname == "ERROR" and "Custom error occurred" in record.message
            for record in caplog.records
        )

def test_error_response_format():
    """Test that error responses follow the expected format"""
    response = client.get("/test-http-error")
    error_response = response.json()
    
    # Check required fields
    assert "type" in error_response
    assert "detail" in error_response
    assert "status_code" in error_response
    
    # Check content type
    assert response.headers["content-type"] == "application/json"

def test_request_id_consistency(caplog):
    """Test that request ID is consistent in logs and response"""
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-validation-error")
        error_response = response.json()
        request_id = error_response["request_id"]
        
        # Check that the same request ID appears in logs
        assert any(
            record.levelname == "ERROR" and request_id in record.message
            for record in caplog.records
        )

def test_error_logging_with_context(caplog):
    """Test that error logs include relevant context"""
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-database-error", headers={"X-Test-Header": "test-value"})
        
        # Check that logs include relevant context
        assert any(
            record.levelname == "ERROR" and
            "method=GET" in record.message and
            "path=/test-database-error" in record.message
            for record in caplog.records
        )

def test_concurrent_requests():
    """Test handling of concurrent requests"""
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(client.get, "/test-validation-error")
            for _ in range(20)
        ]
        responses = [future.result() for future in futures]
    
    # Check that all requests were handled properly
    assert all(response.status_code == 500 for response in responses)
    # Check that each response has a unique request ID
    request_ids = [response.json()["request_id"] for response in responses]
    assert len(request_ids) == len(set(request_ids))

def test_error_handler_order():
    """Test that error handler processes errors in the correct order"""
    # Create a new app with multiple error handlers
    test_app = FastAPI()
    
    # Add our error handler first
    test_app.add_middleware(ErrorHandler)
    
    @test_app.get("/test-error")
    async def test_error():
        raise HTTPException(status_code=400, detail="Test error")
    
    test_client = TestClient(test_app)
    response = test_client.get("/test-error")
    
    # Our error handler should process the error first
    assert response.status_code == 400
    assert "request_id" in response.json()

def test_large_error_message(caplog):
    """Test handling of errors with large messages"""
    @app.get("/test-large-error")
    async def test_large_error():
        raise Exception("x" * 10000)  # Very large error message
    
    with caplog.at_level(logging.ERROR):
        response = client.get("/test-large-error")
        assert response.status_code == 500
        error_response = response.json()
        
        # Check that the error message was truncated in the response
        assert len(error_response["detail"]) < 1000
        
        # Check that the full error was logged
        assert any(
            record.levelname == "ERROR" and len(record.message) >= 10000
            for record in caplog.records
        ) 