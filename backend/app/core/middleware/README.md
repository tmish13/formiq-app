# Middleware Components

This directory contains FastAPI middleware components that provide cross-cutting concerns for the FormIQ application.

## Available Middleware

### 1. Error Handler Middleware

**File:** `error_handler.py`

Provides centralized error handling for the API. It catches various exceptions and converts them to standardized API responses.

**Features:**
- Handles common exceptions with appropriate HTTP status codes
- Provides consistent error response format
- Adds tracebacks in development mode
- Logs errors with appropriate severity levels

**Configuration:**
- Can be configured to include/exclude tracebacks based on environment
- Can customize error response format

### 2. Request Logger Middleware

**File:** `request_logger.py`

Logs details about each incoming request and its corresponding response for monitoring and debugging.

**Features:**
- Logs request method, path, client IP, and user agent
- Captures query parameters
- Optionally logs request bodies in development environment
- Times request processing and includes in log
- Sets appropriate log level based on response status code

**Configuration:**
- Can exclude certain paths (e.g., health check endpoints)
- Can toggle request body logging

### 3. Rate Limiter Middleware

**File:** `rate_limiter.py` 

Implements rate limiting to protect the API from abuse.

**Features:**
- Uses Redis for distributed rate limiting
- Supports per-IP and per-endpoint rate limiting
- Configurable rate limit windows and burst allowances
- Adds rate limit headers to responses

**Configuration:**
- `requests_per_minute`: Default requests allowed per minute
- `window_size`: Time window in seconds
- `burst_size`: Maximum burst allowed
- `exclude_paths`: List of paths to exclude from rate limiting

### 4. Timing Middleware

**File:** `timing.py`

Adds response timing information to help identify performance bottlenecks.

**Features:**
- Measures request processing time
- Adds `X-Response-Time` header to responses
- Optionally logs slow requests

**Configuration:**
- `slow_request_threshold`: Threshold in ms to log slow requests

## Usage

Middleware components are registered in `app/core/middleware.py` in the `setup_middleware()` function. The order of middleware registration is important, as they are executed in reverse order.

```python
def setup_middleware(app: FastAPI) -> None:
    # CORS middleware (outermost)
    app.add_middleware(CORSMiddleware, ...)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware, ...)
    
    # Timing middleware
    app.add_middleware(TimingMiddleware)
    
    # Rate limiting middleware
    app.add_middleware(EnhancedRateLimiter, ...)
    
    # Error handler middleware (innermost)
    app.add_middleware(ErrorHandlerMiddleware)
```

## Creating New Middleware

When creating new middleware, follow these guidelines:

1. Create a new file in this directory for the middleware
2. Extend the `BaseHTTPMiddleware` class from Starlette
3. Implement the `dispatch` method
4. Add proper type hints and docstrings
5. Ensure middleware can be disabled or configured via settings
6. Add appropriate logging
7. Handle exceptions gracefully
8. Register in `app/core/middleware.py`

Example:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from typing import Callable

class MyMiddleware(BaseHTTPMiddleware):
    """Description of what this middleware does."""
    
    def __init__(self, app, option1=default1):
        super().__init__(app)
        self.option1 = option1
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Pre-processing logic
        
        # Call the next middleware or route handler
        response = await call_next(request)
        
        # Post-processing logic
        
        return response
``` 