"""A simple test case to verify ValidationException functionality."""
import pytest
from app.core.exceptions import ValidationException

def test_validation_exception_with_details():
    """Test ValidationException with details parameter."""
    details = {"field": "test", "error": "Invalid value"}
    exception = ValidationException("Test error", details=details)
    assert exception.status_code == 422
    assert exception.detail == "Test error"
    assert exception.details == details

def test_validation_exception_without_details():
    """Test ValidationException without details parameter."""
    exception = ValidationException("Test error")
    assert exception.status_code == 422
    assert exception.detail == "Test error"
    assert exception.details == {} 