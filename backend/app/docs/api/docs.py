from typing import Dict, Any
from fastapi.openapi.utils import get_openapi
from app.core.config import settings

def custom_openapi() -> Dict[str, Any]:
    """Generate custom OpenAPI schema."""
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="""
        FormIQ API Documentation
        
        This API provides endpoints for AI-powered exercise form analysis.
        
        Key Features:
        * User authentication and authorization
        * Exercise form analysis
        * Progress tracking
        * Workout history
        * Real-time feedback
        
        Authentication:
        * All endpoints except /auth/login and /auth/register require authentication
        * Use Bearer token authentication with JWT tokens
        * Tokens expire after 30 minutes
        
        Rate Limiting:
        * 100 requests per minute per IP address
        * Burst limit of 200 requests
        
        Error Responses:
        * 400: Bad Request - Invalid input data
        * 401: Unauthorized - Missing or invalid authentication
        * 403: Forbidden - Insufficient permissions
        * 404: Not Found - Resource does not exist
        * 429: Too Many Requests - Rate limit exceeded
        * 500: Internal Server Error - Server-side error
        
        For more information, visit our documentation at https://docs.formiq.ai
        """,
        routes=[],
        tags=[
            {
                "name": "auth",
                "description": "Authentication and authorization endpoints"
            },
            {
                "name": "users",
                "description": "User management endpoints"
            },
            {
                "name": "exercises",
                "description": "Exercise form analysis endpoints"
            },
            {
                "name": "workouts",
                "description": "Workout tracking endpoints"
            },
            {
                "name": "progress",
                "description": "Progress tracking endpoints"
            },
            {
                "name": "health",
                "description": "Health check endpoints"
            }
        ]
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    # Add response examples
    openapi_schema["components"]["examples"] = {
        "ValidationError": {
            "summary": "Validation Error",
            "value": {
                "detail": [
                    {
                        "loc": ["body", "email"],
                        "msg": "Invalid email format",
                        "type": "value_error"
                    }
                ]
            }
        },
        "AuthenticationError": {
            "summary": "Authentication Error",
            "value": {
                "detail": "Could not validate credentials"
            }
        },
        "RateLimitError": {
            "summary": "Rate Limit Error",
            "value": {
                "detail": "Rate limit exceeded",
                "retry_after": 60
            }
        }
    }
    
    # Add common responses
    openapi_schema["components"]["responses"] = {
        "ValidationError": {
            "description": "Request validation error",
            "content": {
                "application/json": {
                    "example": {
                        "$ref": "#/components/examples/ValidationError"
                    }
                }
            }
        },
        "AuthenticationError": {
            "description": "Authentication error",
            "content": {
                "application/json": {
                    "example": {
                        "$ref": "#/components/examples/AuthenticationError"
                    }
                }
            }
        },
        "RateLimitError": {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "$ref": "#/components/examples/RateLimitError"
                    }
                }
            }
        }
    }
    
    return openapi_schema 